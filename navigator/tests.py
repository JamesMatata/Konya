from django.test import SimpleTestCase

from navigator.services.featherless_ai import (
    _get_askable_null_keys,
    _heuristic_checklist_updates,
    _interview_needs_more_questions,
    _merge_extractor_updates,
    _parse_age_from_message,
    _parse_age_rule_from_text,
    _parse_numeric_threshold_rule,
    apply_checklist_updates,
    build_interviewer_user_message,
    finalize_eligibility_state,
    is_ready_for_blueprint,
)


def _hackathon_criteria_meta():
    return {
        "are_you_at_least_14_years_old": {
            "label": "Are you at least 14 years old?",
            "policy_source": "",
        },
        "currently_enrolled_in_accredited_school": {
            "label": (
                "Are you currently enrolled in an accredited secondary school, "
                "college, university, or graduate/doctoral program?"
            ),
            "policy_source": "",
        },
        "not_employed_full_time_in_ai": {
            "label": (
                "Are you not employed full-time in AI, data science, machine learning, "
                "software engineering, or a directly related technology field?"
            ),
            "policy_source": "",
        },
        "participating_as_team_of_2_5": {
            "label": "Will you be participating as a team of 2-5 members?",
            "policy_source": "",
        },
        "all_team_members_meet_eligibility": {
            "label": "Will all team members meet the eligibility requirements?",
            "policy_source": "",
        },
    }


def _blank_state(criteria_meta=None):
    criteria_meta = criteria_meta or _hackathon_criteria_meta()
    checklist = {key: None for key in criteria_meta}
    return {
        "planner_completed": True,
        "checklist": checklist,
        "criteria_meta": criteria_meta,
        "resolved_sources": {},
        "questions_asked": [],
        "pending_ask_keys": [],
    }


def _reply(state, message, **kwargs):
    meta = state["criteria_meta"]
    conversation = kwargs.pop("conversation_text", None)
    updates = _heuristic_checklist_updates(
        message,
        state["checklist"],
        meta,
        conversation_text=conversation or message,
        **kwargs,
    )
    return apply_checklist_updates(state, updates)


class InterviewHeuristicsTests(SimpleTestCase):
    def test_age_rule_parses_underscore_keys(self):
        self.assertEqual(_parse_age_rule_from_text("are_you_at_least_14_years_old"), ("min", 14))

    def test_heuristic_wins_over_llm_on_conflict(self):
        merged = _merge_extractor_updates({"age": True}, {"age": False})
        self.assertTrue(merged["age"])

    def test_bulk_answer_resolves_student_team_and_employment(self):
        criteria_meta = _hackathon_criteria_meta()
        checklist = {key: None for key in criteria_meta}
        message = (
            "I am a student at Multimedia university of kenya and for now i dont have a team"
        )
        updates = _heuristic_checklist_updates(
            message, checklist, criteria_meta, conversation_text=message
        )
        self.assertTrue(updates["currently_enrolled_in_accredited_school"])
        self.assertTrue(updates["not_employed_full_time_in_ai"])
        self.assertFalse(updates["participating_as_team_of_2_5"])

    def test_age_answer_does_not_repeat(self):
        state = _blank_state()
        bulk = (
            "I am a student at Multimedia university of kenya and for now i dont have a team"
        )
        state = _reply(state, bulk)
        askable = _get_askable_null_keys(state["checklist"], state["criteria_meta"])
        self.assertEqual(askable, ["are_you_at_least_14_years_old"])

        state = _reply(
            state,
            "i am 22 years",
            focus_key="are_you_at_least_14_years_old",
            conversation_text=f"{bulk}\n\ni am 22 years",
        )
        state = finalize_eligibility_state(state)
        self.assertFalse(_interview_needs_more_questions(state))
        self.assertIs(state["checklist"]["are_you_at_least_14_years_old"], True)

    def test_no_team_skips_team_member_question(self):
        state = _reply(_blank_state(), "for now i dont have a team")
        state = finalize_eligibility_state(state)
        askable = _get_askable_null_keys(state["checklist"], state["criteria_meta"])
        self.assertNotIn("all_team_members_meet_eligibility", askable)
        self.assertFalse(state["checklist"]["all_team_members_meet_eligibility"])

    def test_employment_phrase_not_short_no(self):
        state = _blank_state()
        for key, value in {
            "currently_enrolled_in_accredited_school": True,
            "participating_as_team_of_2_5": False,
            "all_team_members_meet_eligibility": False,
            "are_you_at_least_14_years_old": True,
        }.items():
            state["checklist"][key] = value
        updates = _heuristic_checklist_updates(
            "no i am not employed",
            state["checklist"],
            state["criteria_meta"],
            focus_key="not_employed_full_time_in_ai",
        )
        self.assertTrue(updates["not_employed_full_time_in_ai"])

    def test_build_interviewer_tracks_pending_ask_keys(self):
        state = _blank_state()
        message, pending = build_interviewer_user_message(state, is_first_turn=True)
        self.assertGreater(len(pending), 1)
        self.assertIn("?", message)


class ComprehensiveScenarioTests(SimpleTestCase):
    """Judge-style scenarios beyond the original hackathon transcript."""

    def test_all_answers_in_one_complete_message(self):
        state = _reply(
            _blank_state(),
            "I'm 22, a student at Nairobi University, not employed, and I don't have a team yet",
        )
        state = finalize_eligibility_state(state)
        self.assertFalse(_interview_needs_more_questions(state))
        self.assertTrue(is_ready_for_blueprint(state))

    def test_team_of_four_still_asks_member_eligibility(self):
        state = _reply(_blank_state(), "I'm 20 and a student at college")
        state = _reply(state, "yes we have a team of 4")
        askable = _get_askable_null_keys(state["checklist"], state["criteria_meta"])
        self.assertIn("all_team_members_meet_eligibility", askable)
        self.assertTrue(state["checklist"]["participating_as_team_of_2_5"])

    def test_team_flow_completes_with_member_confirmation(self):
        state = _reply(_blank_state(), "student at university, team of 3")
        state = _reply(
            state,
            "yes",
            focus_key="all_team_members_meet_eligibility",
            pending_ask_keys=["all_team_members_meet_eligibility"],
        )
        state = _reply(state, "22 years old", focus_key="are_you_at_least_14_years_old")
        state = _reply(state, "not employed")
        state = finalize_eligibility_state(state)
        self.assertFalse(_interview_needs_more_questions(state))

    def test_too_young_disqualifies_age_criterion(self):
        state = _reply(_blank_state(), "I am 12 years old and a student")
        self.assertFalse(state["checklist"]["are_you_at_least_14_years_old"])

    def test_under_age_max_policy(self):
        meta = {
            "under_18": {"label": "Are you under 18 years old?", "policy_source": ""},
        }
        state = _blank_state(meta)
        state = _reply(state, "I'm 16")
        self.assertTrue(state["checklist"]["under_18"])
        state = _reply(_blank_state(meta), "I'm 22")
        self.assertFalse(state["checklist"]["under_18"])

    def test_age_formats(self):
        meta = {"min_age": {"label": "Are you at least 18 years old?", "policy_source": ""}}
        for phrase in ("I'm 22", "22 years old", "age is 22", "im 22"):
            with self.subTest(phrase=phrase):
                state = _reply(_blank_state(meta), phrase)
                self.assertTrue(state["checklist"]["min_age"])
                self.assertIsNotNone(_parse_age_from_message(phrase))

    def test_employed_in_tech_disqualifies_employment_criterion(self):
        state = _reply(
            _blank_state(),
            "I work full-time as a machine learning engineer at a tech company",
        )
        self.assertFalse(state["checklist"]["not_employed_full_time_in_ai"])

    def test_graduated_not_enrolled(self):
        state = _reply(_blank_state(), "I graduated last year and I'm not in school anymore")
        self.assertFalse(state["checklist"]["currently_enrolled_in_accredited_school"])

    def test_sequential_yes_no_answers(self):
        state = _blank_state()
        state = _reply(
            state,
            "yes",
            focus_key="currently_enrolled_in_accredited_school",
            pending_ask_keys=["currently_enrolled_in_accredited_school"],
        )
        state = _reply(
            state,
            "no",
            focus_key="participating_as_team_of_2_5",
            pending_ask_keys=["participating_as_team_of_2_5"],
        )
        state = _reply(state, "22", focus_key="are_you_at_least_14_years_old")
        state = _reply(state, "unemployed", focus_key="not_employed_full_time_in_ai")
        state = finalize_eligibility_state(state)
        self.assertFalse(_interview_needs_more_questions(state))
        self.assertFalse(state["checklist"]["participating_as_team_of_2_5"])
        self.assertTrue(state["checklist"]["not_employed_full_time_in_ai"])

    def test_negated_employment_bare_yes_does_not_misfire(self):
        state = _blank_state()
        updates = _heuristic_checklist_updates(
            "yes",
            state["checklist"],
            state["criteria_meta"],
            focus_key="not_employed_full_time_in_ai",
            pending_ask_keys=["not_employed_full_time_in_ai"],
        )
        self.assertNotIn("not_employed_full_time_in_ai", updates)

    def test_generic_income_threshold(self):
        meta = {
            "household_income": {
                "label": "Is your household income at least $50,000 per year?",
                "policy_source": "",
            }
        }
        state = _reply(_blank_state(meta), "55000")
        self.assertTrue(state["checklist"]["household_income"])
        state = _reply(_blank_state(meta), "45000")
        self.assertFalse(state["checklist"]["household_income"])

    def test_age_number_does_not_bleed_into_income_criterion(self):
        meta = {
            "min_age": {"label": "Are you at least 14 years old?", "policy_source": ""},
            "household_income": {
                "label": "Is your household income at least $50,000 per year?",
                "policy_source": "",
            },
        }
        state = _reply(_blank_state(meta), "I am 22 years old")
        self.assertTrue(state["checklist"]["min_age"])
        self.assertIsNone(state["checklist"]["household_income"])

    def test_numeric_threshold_rule_parsing(self):
        self.assertEqual(_parse_numeric_threshold_rule("at least $50,000"), ("min", 50000.0))
        self.assertEqual(_parse_numeric_threshold_rule("under 18"), ("max", 18.0))

    def test_single_question_turn_after_bulk(self):
        state = _reply(_blank_state(), "student, no team")
        message, pending = build_interviewer_user_message(state, is_first_turn=False)
        self.assertEqual(len(pending), 1)
        self.assertIn("confirm", message.lower())

    def test_resolved_keys_are_not_overwritten_by_empty_reply(self):
        state = _reply(_blank_state(), "I'm a student, 22, no team, not employed")
        state = finalize_eligibility_state(state)
        prior = dict(state["checklist"])
        state = _reply(state, "ok thanks")
        self.assertEqual(state["checklist"], prior)

    def test_solo_participant_variants(self):
        for phrase in (
            "going solo",
            "on my own for now",
            "without a team",
            "dont have a team",
        ):
            with self.subTest(phrase=phrase):
                state = _reply(_blank_state(), phrase)
                self.assertFalse(state["checklist"]["participating_as_team_of_2_5"])

    def test_team_participation_variants(self):
        for phrase in (
            "we are 3",
            "team of 4",
            "forming a team with friends",
            "yes we have a team",
        ):
            with self.subTest(phrase=phrase):
                state = _reply(_blank_state(), phrase)
                self.assertTrue(state["checklist"]["participating_as_team_of_2_5"])

    def test_age_range_policy(self):
        meta = {
            "age_range": {
                "label": "Are you aged between 18 and 25?",
                "policy_source": "",
            }
        }
        state = _reply(_blank_state(meta), "22")
        self.assertTrue(state["checklist"]["age_range"])
        state = _reply(_blank_state(meta), "30")
        self.assertFalse(state["checklist"]["age_range"])

    def test_generic_citizenship_yes_no(self):
        meta = {
            "kenyan_citizen": {
                "label": "Are you a Kenyan citizen?",
                "policy_source": "",
            }
        }
        state = _reply(
            _blank_state(meta),
            "yes",
            focus_key="kenyan_citizen",
            pending_ask_keys=["kenyan_citizen"],
        )
        self.assertTrue(state["checklist"]["kenyan_citizen"])
        state = _reply(
            _blank_state(meta),
            "no",
            focus_key="kenyan_citizen",
            pending_ask_keys=["kenyan_citizen"],
        )
        self.assertFalse(state["checklist"]["kenyan_citizen"])

    def test_household_size_minimum(self):
        meta = {
            "household_size": {
                "label": "Is your household size at least 3 people?",
                "policy_source": "",
            }
        }
        state = _reply(_blank_state(meta), "4", focus_key="household_size")
        self.assertTrue(state["checklist"]["household_size"])

    def test_interviewer_does_not_reask_resolved_criteria(self):
        state = _reply(_blank_state(), "student, 22, no team, unemployed")
        state = finalize_eligibility_state(state)
        message, pending = build_interviewer_user_message(state, is_first_turn=False)
        self.assertEqual(pending, [])
        self.assertNotIn("confirm", message.lower())
