from os.path import join, exists 
import os
import re
import pytest
from utils import compile_run_program, interactive_program, cmake_build, check_coverage, create_shared_lib
import requests
import json

project_path = "/home/yair/vsCodeProjects/Exercises/apps_in_networks/ex2"

def ref_client(input):
    params = {}
    url = ''
    port = ''
    path = ''
    body = None
    params_match = re.search(r'-r (\d+) (([^\s]+=[^\s]+\s*)+)', input)
    if params_match:
        # print(params_match.group(2),params_match.group(3))
        params = params_match.group(2).strip().split(' ')
        params = [param.split('=') for param in params]
        params = {param[0]: param[1] for param in params}
        assert(len(params) == int(params_match.group(1)))
    
    url_match = re.search(r'http://([^\s:/]+)(:(\d+))?(/[^\s]*)?', input)
    if url_match:
        url = url_match.group(1)
        port = url_match.group(3)
        path = url_match.group(4)
        if not port:
            port = 80
        if not path:
            path = '/'

    post_match = re.search(r'-p (\d+)', input)

    if post_match:
        length = post_match.group(1)
        body = input[post_match.end()+1:post_match.end()+1+int(length)]

    if body:
        res = requests.post(f'http://{url}:{port}{path}', data=body, params=params)
    else:
        res = requests.get(f'http://{url}:{port}{path}', params=params)

    return res


inputs = [
    "http://localhost:5000",
    # "http://localhost:5000/static/image.jpg", #TODO handle binary data
    "http://localhost:5000/long_response",
]

echo_inputs = [
    "http://localhost:5000/echo",
    "-r 3 addr=jecrusalem tel=02-6655443 age=23 http://localhost:5000/echo",
    "-p 6 blabla http://localhost:5000/echo",
    "-p 6 blabla -r 3 addr=jecrusalem tel=02-6655443 age=23 http://localhost:5000/echo",
    "-r 3 addr=jecrusalem tel=02-6655443 age=23 http://localhost:5000/echo -p 6 blabla",
]
expected_failures = [
    "-p 6 blabla -r 2 addr=jecrusalem tel=02-6655443 age=23 http://localhost:5000",
    "http://blala",
    "http://localhost:65536",
    "-r 3 addr=jecrusalem tel=02-6655443 age=23 http://localhost:5000 -p 6 blabla -r 3 addr=jecrusalem tel=02-6655443 age=23 http://localhost:5000",
    "-r 3 addr=jecrusalem tel=02-6655443 age=23 http://localhost:5000 -p 6 blabla -r 3 addr=jecrusalem tel=02-6655443 age=23 http://localhost:5000 -p 6 blabla",

]

@pytest.mark.parametrize("input", echo_inputs)
def test_client_echo(request,input):    
    outdir = f'workloads/client/{request.node.name}'

    files = [join(project_path,file) for file in ['client.c']]

    output = compile_run_program(files, input.split(' '),cwd=outdir)
    assert output.returncode == 0

    # match http response
    response_match = re.search(r'HTTP/1.[01] (\d+) ([A-Z]+)\r\n(([\w\-]+):\s(.+)\r\n)*\r\n(.*)', output.stdout.decode('utf-8'))
    print(output.stdout.decode('utf-8'))
    assert response_match

    imp_output = json.loads(response_match.group(6))
    ref_output = json.loads(ref_client(input).text)

    # print(imp_output)
    # print(ref_output)

    assert imp_output['args'] == ref_output['args']
    assert imp_output.get('data') == ref_output.get('data')
    assert imp_output['message'] == ref_output['message']

@pytest.mark.parametrize("input", inputs)
def test_client(request,input):
    outdir = f'workloads/client/{request.node.name}'
    files = [join(project_path,file) for file in ['client.c']]

    output = compile_run_program(files, input.split(' '),cwd=outdir)
    assert output.returncode == 0

    ref_output = ref_client(input)
    
    sout = output.stdout
    req_pattern = re.compile(b'((GET)|(POST)) (.+) HTTP/1.[01]\r\n((.+): (.+)\r\n)*\r\n(.*)\nLEN = ([0-9]+)')
    req_match = req_pattern.search(sout)

    
    # print(sout.split(b'\r\n\r\n'))
    if req_match:
        method = req_match.group(1)
        path = req_match.group(3)
        headers = req_match.group(5)
        body = req_match.group(8)
        length = req_match.group(9)

        # print(method,headers,body,length)

    res_pattern = re.compile(b'HTTP/1.[01] ([0-9]+) ([A-Z]+)\r\n((.+): (.+)\r\n)*\r\n(.*)\nTotal received response bytes: [0-9]+\n',re.DOTALL)
    res_match = res_pattern.search(sout)
    if res_match:
        status = int(res_match.group(1).decode('utf-8'))
        message = res_match.group(2).decode('utf-8')
        headers = res_match.group(4).decode('utf-8')
        body = res_match.group(6)

        print(ref_output.text)
        assert status == ref_output.status_code
        assert message == ref_output.reason
        # assert headers == ref_output.headers
        assert body == ref_output.text.encode('utf-8')

@pytest.mark.parametrize("input", expected_failures)
def test_client_fail(request,input):
    outdir = f'workloads/client/{request.node.name}'
    files = [join(project_path,file) for file in ['client.c']]

    output = compile_run_program(files, input.split(' '),cwd=outdir)
    assert output.returncode ==0

    out_str = output.stdout.decode('utf-8')
    assert out_str == "Usage: client [-p n <text>] [-r n < pr1=value1 pr2=value2 …>] <URL>\n"


@pytest.mark.skip("coverage")
def test_client_coverage():
    outdir = f'workloads/client_coverage'
    files = [join(project_path,file) for file in ['client.c']]
    tests = [i.split(' ') for i in inputs] + [i[0].split(' ') for i in expected_failures]
    res, uncovered = check_coverage(files, tests, cwd=outdir,show_context=3)
    
    print("\n".join([f"{file}:{idx}\n{context}" for file, idx, line,context in uncovered]))
    print(res)

    # Incorrect coverage
    assert len(uncovered) == 0    



