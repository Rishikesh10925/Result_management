"""
Runs the original PyGPA-Analyzer code (reference/) and ResultCloud's engine
on the same inputs and checks the outputs match. Expected values are never
hand-written here - they always come from the reference code.
"""
import builtins
import random

import numpy as np
import pytest

import source_code as src
import app as ref_app
from services import calculation_engine as ce

rng = random.Random(2026)


def random_sap(dept, category):
    prefix = {('csds', 'old'): '705722', ('csds', 'new'): '705724',
              ('ce', 'old'): '700223', ('ce', 'new'): '700225'}[(dept, category)]
    return prefix + ''.join(rng.choice('0123456789') for _ in range(5))


def random_marks(tee_count, ica_count, avoid_d=False):
    """ICA out of 50 for every subject, TEE out of 100 for TEE subjects."""
    while True:
        ica = [rng.randint(0, 50) for _ in range(tee_count + ica_count)]
        tee = [rng.randint(0, 100) for _ in range(tee_count)]
        if not avoid_d:
            return ica, tee
        # the CLI crashes (KeyError) on an old-scale D grade, so keep 40-49 out
        ica_adj, tee_adj = ce.adjust_marks(ica, tee + [0] * ica_count, tee_count)
        final = ce.cal_total_marks(ica_adj, tee_adj, tee_count, ica_count)
        if not any(40 <= m <= 49 for m in final):
            return ica, tee


# ------------------------------------------------------------ config tables
def test_config_tables_match_source():
    assert ce.CSDS_SUBJECTS == src.csds_semwise_subjects
    assert ce.CSDS_CREDITS == src.csds_sem_sub_credits
    assert ce.CSDS_EXAM_TYPE == src.csds_sem_subs_exam_type
    assert ce.CE_SUBJECTS == src.ce_semwise_subjects
    assert ce.CE_CREDITS == src.ce_sem_sub_credits
    assert ce.CE_EXAM_TYPE == src.ce_sem_subs_exam_type
    assert list(ce.GRADE_SCALE_4.items()) == list(src.grade_dict_scale_4.items())
    assert list(ce.GRADE_SCALE_10.items()) == list(src.grade_dict_scale_10.items())


# ------------------------------------------------------------ sap id
def test_sap_id_matches_app():
    ids = ["70572200027", "70572300021", "70572400001", "70022200001", "70022300001",
           "70022400001", "7057220002", "7057220002a", "12345678901", "70572", ""]
    ids += [str(rng.randint(10**10, 10**11 - 1)) for _ in range(200)]
    ids += [random_sap(d, c) for d in ('csds', 'ce') for c in ('old', 'new') for _ in range(20)]
    for sap in ids:
        assert ce.validate_sap_id(sap) == ref_app.validate_sap_id(sap), sap


# ------------------------------------------------------------ grading
@pytest.mark.parametrize("mark", range(0, 101))
def test_grade_points_match_source(mark):
    got, want = [], []
    src.old_grade_point(mark, want)
    got.append(ce.old_grade_point(mark))
    src.new_grade_point(mark, want)
    got.append(ce.new_grade_point(mark))
    assert got == want


def test_round_and_totals_match_source():
    for _ in range(500):
        n = rng.randint(1, 10)
        ica = [rng.randint(0, 100) for _ in range(n)]
        tee = [rng.randint(0, 100) / 2 for _ in range(n)]
        assert ce.cal_total_marks(ica, tee, n, 0) == src.cal_total_marks(ica, tee, n, 0)
    for x in [0, 0.5, 1.5, 2.49, 64.5, -0.5, -1.5]:
        assert ce.round_TM(x) == src.round_TM(x)


# ------------------------------------------------------------ app.py flow
def app_calculate(sap, sem_num, ica_in, tee_in, previous_sgpas):
    """Transcription of the 'Calculate GPA' branch of reference/app.py main()."""
    _, category, department = ref_app.validate_sap_id(sap)
    sem_subs_exam_type, semwise_subjects, sem_sub_credits = ref_app.get_department_config(department)
    grade_dict_scale = src.grade_dict_scale_4 if category == "old" else src.grade_dict_scale_10
    sem = f'sem{sem_num}'
    tee_sub_count, ica_sub_count = sem_subs_exam_type[sem]
    subjects = semwise_subjects[sem]

    tee_marks = list(tee_in) + [0] * ica_sub_count
    ica_marks = list(ica_in)
    tee_marks_adjusted = [mark / 2 for mark in tee_marks[:tee_sub_count]] + tee_marks[tee_sub_count:]
    ica_marks_adjusted = ica_marks[:tee_sub_count] + [ica * 2 for ica in ica_marks[tee_sub_count:]]
    final_marks = ref_app.cal_total_marks(ica_marks_adjusted, tee_marks_adjusted, tee_sub_count, ica_sub_count)
    sgpa, sub_grades, _ = ref_app.cal_gpa(final_marks, tee_sub_count, ica_sub_count, sem, category,
                                          grade_dict_scale, sem_sub_credits)
    grade_to_point = {value: key for key, value in grade_dict_scale.items()}
    grade_points = [grade_to_point[grade] for grade in sub_grades]
    totals = list(np.array(sem_sub_credits[sem][:-1]) * np.array(grade_points))

    cgpa = None
    if sem_num > 1:
        num, den = 0, 0
        for prev_sem_num, prev_sgpa in enumerate(previous_sgpas, 1):
            c = sem_sub_credits[f'sem{prev_sem_num}'][-1]
            num += prev_sgpa * c
            den += c
        c = sem_sub_credits[sem][-1]
        num += sgpa * c
        den += c
        cgpa = num / den

    return {'subjects': subjects[:tee_sub_count + ica_sub_count], 'credits': sem_sub_credits[sem][:-1],
            'final': final_marks, 'grades': sub_grades, 'points': grade_points, 'totals': totals,
            'sgpa': sgpa, 'cgpa': cgpa}


def compare_with_app(sap, sem_num, ica, tee, prev):
    want = app_calculate(sap, sem_num, ica, tee, prev)
    got = ce.calculate_result(sap, sem_num, ica, tee, prev)
    rows = got['rows']
    assert [r['subject'] for r in rows] == want['subjects']
    assert [r['credits'] for r in rows] == want['credits']
    assert [r['final_marks'] for r in rows] == want['final']
    assert [r['grade'] for r in rows] == want['grades']
    assert [r['grade_point'] for r in rows] == want['points']
    assert [r['total'] for r in rows] == pytest.approx(want['totals'])
    assert got['sgpa'] == want['sgpa']
    assert got['cgpa'] == want['cgpa']
    assert f"{got['sgpa']:.2f}" == f"{want['sgpa']:.2f}"


@pytest.mark.parametrize("category", ["old", "new"])
@pytest.mark.parametrize("sem_num", range(1, 9))
def test_csds_result_matches_app(sem_num, category):
    tee_count, ica_count = ce.CSDS_EXAM_TYPE[f'sem{sem_num}']
    scale_max = 4.0 if category == "old" else 10.0
    for _ in range(25):
        ica, tee = random_marks(tee_count, ica_count)
        prev = [round(rng.uniform(0, scale_max), 2) for _ in range(sem_num - 1)]
        compare_with_app(random_sap('csds', category), sem_num, ica, tee, prev)


@pytest.mark.parametrize("category", ["old", "new"])
@pytest.mark.parametrize("sem_num", range(1, 9))
def test_ce_result_matches_app_with_ce_credits(sem_num, category, monkeypatch):
    # app.py gives CE students CE credits; flip the switch to compare like for like
    monkeypatch.setattr(ce, 'CE_USES_CSDS_CREDITS', False)
    tee_count, ica_count = ce.CE_EXAM_TYPE[f'sem{sem_num}']
    scale_max = 4.0 if category == "old" else 10.0
    for _ in range(25):
        ica, tee = random_marks(tee_count, ica_count)
        prev = [round(rng.uniform(0, scale_max), 2) for _ in range(sem_num - 1)]
        compare_with_app(random_sap('ce', category), sem_num, ica, tee, prev)


# ------------------------------------------------------------ source_code.py CLI
def run_cli(monkeypatch, capsys, sap, sem_num, ica, tee, pre_cgpa=None):
    """Drives run_cli_gpa_calculator() option 3 with scripted input()."""
    tee_count, ica_count = (src.csds_sem_subs_exam_type if sap.startswith('7057')
                            else src.ce_sem_subs_exam_type)[f'sem{sem_num}']
    answers = ['Test', sap, '3', str(sem_num)]
    if sem_num != 1:
        answers.append(str(pre_cgpa))
    for i in range(tee_count):
        answers += [str(ica[i]), str(tee[i])]
    answers += [str(m) for m in ica[tee_count:]]
    it = iter(answers)
    monkeypatch.setattr(builtins, 'input', lambda *_: next(it))
    src.run_cli_gpa_calculator()
    out = capsys.readouterr().out
    sgpa = out.split('==> SGPA:')[1].split()[0]
    cgpa = out.split('==> CGPA:')[1].split()[0] if '==> CGPA:' in out else None
    return sgpa, cgpa


def cli_cases():
    # CE sem2/3/4 have more subjects than CSDS credits, and the CLI crashes
    # there (see test_ce_mismatched_semesters_fail_like_cli)
    for dept in ('csds', 'ce'):
        for sem_num in range(1, 9):
            if dept == 'ce' and sem_num in (2, 3, 4):
                continue
            for category in ('old', 'new'):
                yield dept, sem_num, category


@pytest.mark.parametrize("dept, sem_num, category", list(cli_cases()))
def test_result_matches_cli(dept, sem_num, category, monkeypatch, capsys):
    exam = ce.CSDS_EXAM_TYPE if dept == 'csds' else ce.CE_EXAM_TYPE
    tee_count, ica_count = exam[f'sem{sem_num}']
    scale_max = 4.0 if category == "old" else 10.0
    for _ in range(10):
        sap = random_sap(dept, category)
        ica, tee = random_marks(tee_count, ica_count, avoid_d=(category == 'old'))
        pre = round(rng.uniform(0, scale_max), 2) if sem_num > 1 else None
        want_sgpa, want_cgpa = run_cli(monkeypatch, capsys, sap, sem_num, ica, tee, pre)

        got = ce.calculate_result(sap, sem_num, ica, tee, [pre] * (sem_num - 1) if pre else [])
        assert str(round(got['sgpa'], 2)) == want_sgpa
        if sem_num == 2:
            # CLI only weights the previous semester, so it lines up with
            # app.py's formula when there is exactly one previous semester
            assert "{:.3f}".format(got['cgpa'])[:-1] == want_cgpa


def test_ce_mismatched_semesters_fail_like_cli(monkeypatch, capsys):
    for sem_num in (2, 3, 4):
        tee_count, ica_count = ce.CE_EXAM_TYPE[f'sem{sem_num}']
        ica, tee = [40] * (tee_count + ica_count), [80] * tee_count
        with pytest.raises(IndexError):
            run_cli(monkeypatch, capsys, '70022500001', sem_num, ica, tee, 8.0)
        with pytest.raises(IndexError):
            ce.calculate_result('70022500001', sem_num, ica, tee, [8.0] * (sem_num - 1))


# ------------------------------------------------------------ goal matrix
@pytest.mark.parametrize("dept", ["csds", "ce"])
@pytest.mark.parametrize("category", ["old", "new"])
@pytest.mark.parametrize("sem_num", range(1, 9))
def test_goal_matrix_matches_app(dept, category, sem_num):
    exam, subjects, _ = ce.get_department_config(dept)
    low_marks, scale = ce.get_grade_config(category)
    sem = f'sem{sem_num}'
    tee_count = exam[sem][0]
    for _ in range(10):
        ica = [rng.randint(0, 50) for _ in range(tee_count)]
        got = ce.calculate_goal_matrix(ica, low_marks)
        if tee_count == 0:
            assert got == []
            continue
        df = ref_app.calculate_goal_matrix(ica, tee_count, subjects, low_marks, scale, sem)
        # numpy turns a mixed int/'-' row into strings, so compare as text
        assert [[str(v) for v in row] for row in got] == df.values.astype(str).tolist()
        assert list(df.columns) == list(scale.values())
        assert list(df.index) == subjects[sem][:tee_count]


# ------------------------------------------------------------ planner
@pytest.mark.parametrize("dept", ["csds", "ce"])
@pytest.mark.parametrize("category", ["old", "new"])
@pytest.mark.parametrize("sem_num", range(1, 9))
def test_planner_matches_source_with_same_seed(dept, category, sem_num, capsys):
    exam, subjects, credits = ce.get_department_config(dept)
    _, scale = ce.get_grade_config(category)
    sem = f'sem{sem_num}'
    tee_count, ica_count = exam[sem]
    subs = subjects[sem]
    levels = [rng.choice(['easy', 'medium', 'hard']) for _ in subs]
    target = 7.0 if category == 'new' else 3.0
    args = (subs, target, levels, tee_count, ica_count, sem, category, scale, credits)

    if dept == 'ce' and sem_num in (2, 3, 4):
        with pytest.raises(IndexError):
            src.generate_multiple_planes(*args)
        with pytest.raises(IndexError):
            ce.generate_multiple_plans(*args)
        return

    random.seed(sem_num * 31)
    want = src.generate_multiple_planes(*args)
    random.seed(sem_num * 31)
    got = ce.generate_multiple_plans(*args)
    assert [{'plan': p['plan'], 'gpa': p['gpa']} for p in got] == want
