# Requirements Traceability Map — Input Security Rules (FR-1..FR-20)

Maps each functional requirement to its test file, test function name, goal area,
and requirement area label so reviewers can audit FR coverage at a glance.

## Coverage Table

| FR    | Test File                          | Test Function                                        | Goal  | Area                       |
|-------|------------------------------------|------------------------------------------------------|-------|----------------------------|
| FR-1  | test_fr1_fr4_access_init.py        | test_fr1_page_loads_and_becomes_interactive          | G-1   | Access / Init State        |
| FR-2  | test_fr1_fr4_access_init.py        | test_fr2_no_blocking_load_state_after_render         | G-1   | Access / Init State        |
| FR-3  | test_fr1_fr4_access_init.py        | test_fr3_refresh_restores_page_to_usable_state       | G-1   | Access / Init State        |
| FR-4  | test_fr1_fr4_access_init.py        | test_fr4_clean_session_reopen_works_correctly        | G-1   | Access / Init State        |
| FR-5  | test_fr5_fr8_structure.py          | test_fr5_page_identity_is_visible                    | G-2   | Visible Structure          |
| FR-6  | test_fr5_fr8_structure.py          | test_fr6_major_sections_are_present                  | G-2   | Visible Structure          |
| FR-7  | test_fr5_fr8_structure.py          | test_fr7_primary_controls_visible_and_enabled        | G-2   | Visible Structure          |
| FR-8  | test_fr5_fr8_structure.py          | test_fr8_desktop_viewport_layout                     | G-2   | Visible Structure          |
| FR-8  | test_fr5_fr8_structure.py          | test_fr8_mobile_viewport_layout                      | G-2   | Visible Structure          |
| FR-9  | test_fr9_fr12_control_input.py     | test_fr9_search_control_can_be_interacted_with       | G-3   | Control / Input Interaction|
| FR-10 | test_fr9_fr12_control_input.py     | test_fr10_search_input_has_accessible_label_or_placeholder | G-3 | Control / Input Interaction|
| FR-11 | test_fr9_fr12_control_input.py     | test_fr11_valid_search_submission_shows_results      | G-3   | Control / Input Interaction|
| FR-12 | test_fr9_fr12_control_input.py     | test_fr12_invalid_input_handled_safely[empty]        | G-4   | Control / Input Interaction|
| FR-12 | test_fr9_fr12_control_input.py     | test_fr12_invalid_input_handled_safely[html_injection] | G-4 | Control / Input Interaction|
| FR-12 | test_fr9_fr12_control_input.py     | test_fr12_invalid_input_handled_safely[overlong_512] | G-4   | Control / Input Interaction|
| FR-12 | test_fr9_fr12_control_input.py     | test_fr12_invalid_input_handled_safely[sql_injection_chars] | G-4 | Control / Input Interaction|
| FR-12 | test_fr9_fr12_control_input.py     | test_fr12_invalid_input_handled_safely[control_chars] | G-4  | Control / Input Interaction|
| FR-12 | test_fr9_fr12_control_input.py     | test_fr12_invalid_input_handled_safely[emoji_overlong] | G-4 | Control / Input Interaction|
| FR-12 | test_fr9_fr12_control_input.py     | test_fr12_invalid_input_handled_safely[whitespace_only] | G-4 | Control / Input Interaction|
| FR-13 | test_fr13_fr16_content_nav.py      | test_fr13_content_cards_are_visible_after_load       | G-2   | Content / Media / Navigation|
| FR-14 | test_fr13_fr16_content_nav.py      | test_fr14_selecting_card_opens_detail_or_player      | G-2   | Content / Media / Navigation|
| FR-15 | test_fr13_fr16_content_nav.py      | test_fr15_tab_navigation_is_functional               | G-5   | Content / Media / Navigation|
| FR-15 | test_fr13_fr16_content_nav.py      | test_fr15_pagination_next_page_loads_more            | G-5   | Content / Media / Navigation|
| FR-16 | test_fr13_fr16_content_nav.py      | test_fr16_modal_or_expanded_panel_can_be_dismissed   | G-5   | Content / Media / Navigation|
| FR-17 | test_fr17_fr20_empty_invalid.py    | test_fr17_empty_state_message_shown_when_no_content  | G-4   | Empty / Invalid / Failure  |
| FR-18 | test_fr17_fr20_empty_invalid.py    | test_fr18_failed_resource_shows_error_indicator      | G-4   | Empty / Invalid / Failure  |
| FR-19 | test_fr17_fr20_empty_invalid.py    | test_fr19_retry_action_triggers_recovery             | G-5   | Empty / Invalid / Failure  |
| FR-20 | test_fr17_fr20_empty_invalid.py    | test_fr20_popup_resilience                           | G-5   | Empty / Invalid / Failure  |
| FR-20 | test_fr17_fr20_empty_invalid.py    | test_fr20_delayed_asset_resilience                   | G-5   | Empty / Invalid / Failure  |
| FR-20 | test_fr17_fr20_empty_invalid.py    | test_fr20_missing_resource_resilience                | G-5   | Empty / Invalid / Failure  |

## Goal Definitions

| Goal | Description |
|------|-------------|
| G-1  | Successful page load and init state |
| G-2  | Main interaction and structural coverage |
| G-3  | Visible content and navigation validation |
| G-4  | Safe invalid-input and failure-state handling |
| G-5  | Lifecycle actions — refresh, retry, transient-state cleanup |

## Requirement Area Summary

| Area                        | FRs Covered | Spec File |
|-----------------------------|-------------|-----------|
| Access / Init State         | FR-1..FR-4  | test_fr1_fr4_access_init.py |
| Visible Structure           | FR-5..FR-8  | test_fr5_fr8_structure.py |
| Control / Input Interaction | FR-9..FR-12 | test_fr9_fr12_control_input.py |
| Content / Media / Navigation| FR-13..FR-16| test_fr13_fr16_content_nav.py |
| Empty / Invalid / Failure   | FR-17..FR-20| test_fr17_fr20_empty_invalid.py |

## Running the Suite

```bash
# From the repository root
pytest tests/playwright/input_sec_rules/ -v

# With environment overrides
AI_TUBE_URL=http://localhost:3000 pytest tests/playwright/input_sec_rules/ -v

# Run a specific FR group
pytest tests/playwright/input_sec_rules/test_fr9_fr12_control_input.py -v

# Run parametrized invalid-input tests only
pytest tests/playwright/input_sec_rules/test_fr9_fr12_control_input.py::test_fr12_invalid_input_handled_safely -v
```
