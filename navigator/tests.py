from django.test import SimpleTestCase

from navigator.services.featherless_ai import (
    _get_askable_null_keys,
    _heuristic_checklist_updates,
    _interview_needs_more_questions,
    _merge_extractor_updates,
    _parse_age_rule_from_text,
    apply_checklist_updates,
    build_interviewer_user_message,
    finalize_eligibility_state,
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


def _blank_hackathon_state():
    criteria_meta = _hackathon_criteria_meta()
    checklist = {key: None for key in criteria_meta}
    return {
        "planner_completed": True,
        "checklist": checklist,
        "criteria_meta": criteria_meta,
        "resolved_sources": {},
        "questions_asked": [],
        "pending_ask_keys": [],
    }


class InterviewHeuristicsTests(SimpleTestCase):
    def test_age_rule_parses_underscore_keys(self):
        self.assertEqual(_parse_age_rule_from_text("are_you_at_least_14_years_old"), ("min", 14))

    def test_heuristic_wins_over_llm_on_conflict(self):
        merged = _merge_extractor_updates(
            {"age": True},
            {"age": False},
        )
        self.assertTrue(merged["age"])

    def test_bulk_answer_resolves_student_team_and_employment(self):
        criteria_meta = _hackathon_criteria_meta()
        checklist = {key: None for key in criteria_meta}
        message = (
            "I am a student at Multimedia university of kenya and for now i dont have a team"
        )
        updates = _heuristic_checklist_updates(
            message,
            checklist,
            criteria_meta,
            conversation_text=message,
        )
        self.assertTrue(updates["currently_enrolled_in_accredited_school"])
        self.assertTrue(updates["not_employed_full_time_in_ai"])
        self.assertFalse(updates["participating_as_team_of_2_5"])

    def test_age_answer_does_not_repeat(self):
        state = _blank_hackathon_state()
        bulk = (
            "I am a student at Multimedia university of kenya and for now i dont have a team"
        )
        state = apply_checklist_updates(
            state,
            _heuristic_checklist_updates(bulk, state["checklist"], state["criteria_meta"], conversation_text=bulk),
        )
        askable = _get_askable_null_keys(state["checklist"], state["criteria_meta"])
        self.assertEqual(askable, ["are_you_at_least_14_years_old"])

        age_message = "i am 22 years"
        state = apply_checklist_updates(
            state,
            _heuristic_checklist_updates(
                age_message,
                state["checklist"],
                state["criteria_meta"],
                focus_key="are_you_at_least_14_years_old",
                conversation_text=f"{bulk}\n\n{age_message}",
            ),
        )
        state = finalize_eligibility_state(state)
        self.assertFalse(_interview_needs_more_questions(state))
        self.assertIs(state["checklist"]["are_you_at_least_14_years_old"], True)

    def test_no_team_skips_team_member_question(self):
        state = _blank_hackathon_state()
        bulk = "for now i dont have a team"
        state = apply_checklist_updates(
            state,
            _heuristic_checklist_updates(bulk, state["checklist"], state["criteria_meta"]),
        )
        state = finalize_eligibility_state(state)
        askable = _get_askable_null_keys(state["checklist"], state["criteria_meta"])
        self.assertNotIn("all_team_members_meet_eligibility", askable)
        self.assertFalse(state["checklist"]["all_team_members_meet_eligibility"])

    def test_employment_phrase_not_short_no(self):
        criteria_meta = _hackathon_criteria_meta()
        checklist = {key: None for key in criteria_meta}
        checklist["currently_enrolled_in_accredited_school"] = True
        checklist["participating_as_team_of_2_5"] = False
        checklist["all_team_members_meet_eligibility"] = False
        checklist["are_you_at_least_14_years_old"] = True

        updates = _heuristic_checklist_updates(
            "no i am not employed",
            checklist,
            criteria_meta,
            focus_key="not_employed_full_time_in_ai",
        )
        self.assertTrue(updates["not_employed_full_time_in_ai"])

    def test_build_interviewer_tracks_pending_ask_keys(self):
        state = _blank_hackathon_state()
        message, pending = build_interviewer_user_message(state, is_first_turn=True)
        self.assertGreater(len(pending), 1)
        self.assertIn("?", message)
        self.assertTrue(any("accredited" in _hackathon_criteria_meta()[key]["label"] for key in pending))
