from os.path import join, exists 
import os
import re
import pytest
from utils import compile_run_program, interactive_program, cmake_build, check_coverage, create_shared_lib
from ctypes import Structure, POINTER, c_void_p, c_uint, c_char_p, c_int, pointer, cast

path = "/home/yair/vsCodeProjects/Exercises/apps_in_networks/ex1_dor"

class slist_node(Structure):pass
slist_node._fields_ = [
        ('data', c_void_p),
        ('next', POINTER(slist_node)),
        ('prev', POINTER(slist_node))
        ]

class slist(Structure):
    _fields_ = [
        ('head',POINTER(slist_node)), 
        ('tail',POINTER(slist_node)), 
        ('size',c_uint)
        ]

class pm_state(Structure):pass
pm_state._fields_ = [
        ('id',c_uint),
        ('depth',c_uint), 
        ('output',POINTER(slist)), 
        ('fail',POINTER(pm_state)), 
        ('_transitions',POINTER(slist))
        ]

class pm(Structure):
    _fields_ = [
        ('newstate',c_uint), 
        ('zerostate',POINTER(pm_state)),
        ]


class pm_match(Structure):
    _fields_ = [
        ('pattern',c_char_p),
        ('start_pos',c_int),
        ('end_pos',c_int),
        ('fstate',POINTER(pm_state))
        ]



def string_match_ref(string, patterns):
    matchs = []
    patterns = list(set(patterns))
    for pattern in patterns:
        mtcs = re.finditer(r'(?=('+pattern + r'))', string)
        matchs.extend([{'start': m.start(1), 'end': m.end(1)-1, 'match': m.group(1)} for m in mtcs])
    return sorted(matchs, key=lambda x: (x['start'], x['end'], x['match']))

tests = [
("aabbababbab",['aab', 'aba', 'baa']),
    ("abccbabbba",['a','b','c']),
    ("xyzabcabde",[ "abc", "bca", "cab", "acb"]),
    ("aaaaaaaa",['a','aaa','aaaa', 'aaaaaaaaaaaaaa']),
    ("xyzabcabde",['yzabc','zab']),
    ("xyzabcabde",['xyzabc','zabc','zab']),
    ("xyzabcabde",['zxy','zxy']),
    ("the quick brown fox hoped over the red wall",['the','the quick','quick']),
    ("",[]),
    ("aaaaaa",[]),
    ("aaaaaa",['a']),
    ("",['a']),
    ("a",['a']),
    ("a",['aa']),
    ("a",['b']),
    ("ababbadb",['aba','ab','abb','acc','aca','ada','adb']),
    ("ababbaababab",['ababab','ab','ba','aa','a','b']),
    ("xxyxxyxyyyxxy",['xxy','yxx','xy','yxy','xx','yyy']),
    ("afaffafffaafafa",['af','afa','tfa','aaaf','ff','fft']),
    ("xyzabcabdebdeee",['yzabc','zab','abz','azz','bde']),
    ("xyzabcabdebdeee",['xyzabcabdebdeee']),
    ("xyzabcabdebdeee",['x','y','z','a','xyz','xyza','xyzabcabdebdeee']),
    ("abcabde",["abc", "bca", "cab" , "acb"]),]

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
    matchs_imp = sorted([{'start': int(m[1]), 'end': int(m[2]), 'match': m[0]} for m in matchs], key=lambda x: (x['start'], x['end'], x['match']))
    
    # Incorrect output
    assert matchs_imp == matchs_ref

@pytest.mark.parametrize('params', tests)
def test_so_run(request,params):
    files = [join(path,file) for file in ['main.c', 'slist.c','pattern_matching.c']]
    outdir = f'workloads/so_run/{request.node.name}'

    funcs = create_shared_lib(files, outdir)

    string, patterns = params

    stdout = os.dup(1)
    out = os.open(join(outdir,'stdout.txt'), os.O_CREAT | os.O_WRONLY)
    os.dup2(out, 1)
    os.close(out)
    matcher = pm()
    funcs.pm_init(pointer(matcher))

    for pattern in patterns:
        funcs.pm_addstring(pointer(matcher), pattern.encode('utf-8'), len(pattern))
    funcs.pm_makeFSM(pointer(matcher))

    funcs.pm_fsm_search.restype = POINTER(slist)
    ret_val = funcs.pm_fsm_search(matcher.zerostate, string.encode('utf-8'), len(string))
    os.dup2(stdout, 1)
    os.close(stdout)

    head = ret_val.contents.head
    matchs = []
    while head:
        match = cast(head.contents.data, POINTER(pm_match)).contents
        matchs.append({'start': match.start_pos, 'end': match.end_pos, 'match': match.pattern.decode('utf-8')})
        head = head.contents.next
    matchs.sort(key=lambda x: (x['start'], x['end'], x['match']))

    matchs_ref = string_match_ref(string, patterns)

    # Incorrect output
    assert matchs == matchs_ref


def test_string_match_coverage(request):
    files = [join(path,file) for file in ['main.c', 'slist.c','pattern_matching.c']]
    outdir = f'workloads/string_match_coverage/{request.node.name}'

    tests_argv = [ [string,*patterns] for string, patterns in tests]

    res, uncovered = check_coverage(files, tests_argv, cwd=outdir)

    print(uncovered)
    print(res)

    # Incorrect coverage
    assert len(uncovered) == 0