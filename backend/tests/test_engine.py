import pytest

from services import calculation_engine as ce


# ---- sap id
@pytest.mark.parametrize("sap, expected", [
    ("70572200027", (True, "old", "csds")),
    ("70572300021", (True, "old", "csds")),
    ("70572400001", (True, "new", "csds")),
    ("70022200001", (True, "old", "ce")),
    ("70022300001", (True, "old", "ce")),
    ("70022500001", (True, "new", "ce")),
    ("7057220002", (False, None, None)),     # 10 chars
    ("705722000277", (False, None, None)),   # 12 chars
    ("7057220002a", (False, None, None)),    # not digits
    ("12342200027", (False, None, None)),    # unknown dept
])
def test_validate_sap_id(sap, expected):
    assert ce.validate_sap_id(sap) == expected


# ---- grading boundaries
@pytest.mark.parametrize("mark, gp", [
    (100, 4.0), (85, 4.0), (84, 3.75), (81, 3.75), (77, 3.5), (73, 3.25), (69, 3.0),
    (65, 2.75), (61, 2.5), (57, 2.25), (50, 2.0), (49, 1.15), (40, 1.15), (39, 0), (0, 0),
])
def test_old_grade_point(mark, gp):
    assert ce.old_grade_point(mark) == gp


@pytest.mark.parametrize("mark, gp", [
    (100, 10), (90, 10), (89, 9), (80, 9), (70, 8), (60, 7), (55, 6), (50, 5),
    (40, 4), (39, 0), (0, 0),
])
def test_new_grade_point(mark, gp):
    assert ce.new_grade_point(mark) == gp


def test_d_grade_label_falls_back_to_F():
    # 1.15 is not a key in the 4.0 grade dict; app.py shows it as 'F'
    # but still counts 1.15 towards the SGPA.
    gpa, labels, total = ce.cal_gpa([45], 1, 0, 'sem8', 'old', ce.GRADE_SCALE_4, {'sem8': [10, 10]})
    assert labels == ['F']
    assert gpa == pytest.approx(1.15)


# ---- marks
def test_adjust_marks():
    ica, tee = ce.adjust_marks([40, 30, 45], [80, 71, 0], tee_sub_count=2)
    assert ica == [40, 30, 90]      # ICA-only doubled
    assert tee == [40.0, 35.5, 0]   # TEE halved, ICA-only TEE = 0


def test_round_TM():
    assert ce.round_TM(65.5) == 66
    assert ce.round_TM(64.5) == 65   # half up, not banker's rounding
    assert ce.round_TM(64.49) == 64
    assert ce.round_TM(-2.5) == -3


def test_cal_total_marks():
    assert ce.cal_total_marks([30, 30.0], [35.5, 34.5], 2, 0) == [66, 65]


# ---- sgpa / cgpa
def test_sgpa_is_credit_weighted():
    credits = {'semX': [4, 2, 6]}
    gpa, labels, total = ce.cal_gpa([95, 45], 2, 0, 'semX', 'new', ce.GRADE_SCALE_10, credits)
    assert total == 4 * 10 + 2 * 4
    assert gpa == pytest.approx(48 / 6)
    assert labels == ['O', 'P']


def test_cgpa_multiple_semesters():
    credits = ce.CSDS_CREDITS
    cgpa = ce.calculate_cgpa([8.0, 9.0], 7.0, 3, credits)
    assert cgpa == pytest.approx((8 * 19 + 9 * 21 + 7 * 20) / (19 + 21 + 20))


def test_calculate_result_csds_sem1():
    res = ce.calculate_result("70572400001", 1, [40, 40, 40, 40, 40, 45, 45, 45, 45], [80, 80, 80, 80, 80])
    assert [r['final_marks'] for r in res['rows']] == [80] * 5 + [90] * 4
    assert res['sgpa'] == pytest.approx((4 + 4 + 3 + 3 + 3) * 9 / 19 + (1 + 1) * 10 / 19)
    assert res['cgpa'] is None


def test_ce_uses_csds_credits():
    _, _, credits = ce.get_department_config("ce")
    assert credits is ce.CSDS_CREDITS


# ---- goal matrix
def test_goal_matrix_values():
    m = ce.calculate_goal_matrix([40, 0], ce.LOW_MARKS['new'])
    # ica 40: 90->100, 80->80, ..., 40->0, 0->0 (negative clamped)
    assert m[0] == [100, 80, 60, 40, 30, 20, 0, 0]
    # ica 0: anything needing over 100 shows '-'
    assert m[1] == ['-', '-', '-', '-', '-', 100, 80, 0]


# ---- planner
def test_generate_marks_ranges():
    for _ in range(200):
        ica, tee = ce.generate_marks("easy")
        assert 43 <= ica <= 50 and 40 <= tee <= 50
        ica, tee = ce.generate_marks("medium")
        assert 35 <= ica <= 43 and 35 <= tee <= 43
        ica, tee = ce.generate_marks("hard")
        assert 25 <= ica <= 35 and 25 <= tee <= 35


def test_generate_multiple_plans_shape():
    subs = ce.CSDS_SUBJECTS['sem4']
    plans = ce.generate_multiple_plans(subs, 8.0, ['easy'] * 6, 6, 0, 'sem4', 'new', ce.GRADE_SCALE_10, ce.CSDS_CREDITS)
    assert len(plans) == 4
    assert all(len(p['plan']) == 6 for p in plans)
