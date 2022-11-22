from os.path import join, exists 
import re
import pytest
from utils import compile_run_program, interactive_program, cmake_build, check_coverage

path = "/home/yair/vsCodeProjects/Exercises/apps_in_networks/ex1"


def string_match_ref(string, patterns):
    matchs = []
    for pattern in patterns:
        mtcs = re.finditer(r'(?=('+pattern + r'))', string)
        matchs.extend([{'start': m.start(1), 'end': m.end(1), 'match': m.group(1)} for m in mtcs])
    return sorted(matchs, key=lambda x: (x['start'], x['end'], x['match']))

tests = [
    ("aabbababbab",['aab', 'aba', 'baa']),
    ("abccbabbba",['a','b','c']),
    ("xyzabcabde",[ "abc", "bca", "cab", "acb"]),
    ("aaaaaaaa",['a','aa','aaa','aaaa', 'aaaaaaaaaaaaaa']),
    ("xyzabcabde",['yzabc','zab']),
    ("xyzabcabde",['xyzabc','zabc','zab']),
    ("xyzabcabde",['zxy','zxy']),
]

@pytest.mark.parametrize('params', tests)
def test_string_match(request,params):
    string, patterns = params
    
    files = [join(path,file) for file in ['main.c', 'slist.c','pattern_matching.c']]
    outdir = f'workloads/string_match/{request.node.name}'

    res =  compile_run_program(files, args = [string,*patterns],cwd=outdir)
    
    # Compilation error, runtime error, or memory error
    assert res.returncode == 0
    
    matchs_ref = string_match_ref(string, patterns)
    
    matchs = re.findall(r'Matched pattern (.+) at position (\d+) to (\d+)', res.stdout.decode('utf-8'))
    matchs_imp = sorted([{'start': int(m[1]), 'end': int(m[2])+1, 'match': m[0]} for m in matchs], key=lambda x: (x['start'], x['end'], x['match']))
    
    # Incorrect output
    assert matchs_imp == matchs_ref

def test_string_match_coverage(request):
    files = [join(path,file) for file in ['main.c', 'slist.c','pattern_matching.c']]
    outdir = f'workloads/string_match_coverage/{request.node.name}'

    tests_argv = [ [string,*patterns] for string, patterns in tests]

    res, uncovered = check_coverage(files, tests_argv, cwd=outdir)

    print(uncovered)
    print(res)

    # Incorrect coverage
    assert len(uncovered) == 0