import subprocess
import os
import tempfile
from os.path import join, exists 
import re
from ctypes import *

def compile_run_program(program, args, input=None, cwd=None):
    # Create a woring directory
    if cwd is None:
        # Create a temporary directory
        cwd = tempfile.mkdtemp()
    if not exists(cwd):
        os.makedirs(cwd)
    if isinstance(program, str):
        program = [program]
    # Compile the program
    subprocess.check_call(['gcc', '-g', *program, '-o', os.path.join(cwd, 'program.out')])

    command = ['valgrind','--error-exitcode=1','--track-origins=yes','--leak-check=full',join(cwd, 'program.out')] + args

    # Run the program
    result = subprocess.run(command,input=input,stdout=subprocess.PIPE,stderr=open(join(cwd, 'stderr.txt'), 'wb'))
    
    # Create a reproducer file
    with open(join(cwd, 'reproducer.sh'), 'w') as f:
        f.write(' '.join(command))

    # Make the file executable
    os.chmod(join(cwd, 'reproducer.sh'), 0o755)


    # Write the output to a file
    with open(join(cwd, 'stdout.txt'), 'wb') as f:
        f.write(result.stdout)

    # Return the result
    return result

def check_coverage(program, tests, input=None, cwd=None, show_context=0):
    if cwd is None:
        # Create a temporary directory
        cwd = tempfile.mkdtemp()
    if not exists(cwd):
        os.makedirs(cwd)
    if isinstance(program, str):
        program = [program]

    # Compile the program
    subprocess.check_call(['gcc', '-fprofile-arcs', '-ftest-coverage', '-g', *program, '-o', 'program.out'],cwd=cwd)

    # Run the tests
    for test in tests:
        subprocess.run([join(cwd, 'program.out')] + test, input=input, stdout=open(join(cwd, 'stdout.txt'), 'wb'), stderr=open(join(cwd, 'stderr.txt'), 'wb'))

    # Run gcov on all the files
    progs = [f"program.out-{f.split('/')[-1]}" for f in program]


    res = subprocess.run(['gcov', *progs],stdout=subprocess.PIPE, cwd=cwd)
    print(res.stdout.decode())
    uncovered = []

    # Read the coverage
    for file in progs:
        # if not exists(join(cwd,file + '.gcov')):
        file = file.split('-',1)[1]
        if not exists(join(cwd,file + '.gcov')):
            continue
        with open(join(cwd,file + '.gcov'), 'r') as f:
            data = f.read()
            matchs = re.findall(r'^\s*#{5}:\s*(\d+):(.+)$', data, re.MULTILINE)
            for line, code in matchs:
                if show_context > 0:
                    lines = [line for line in data.split('\n') if not re.match(r'\s*-:\s*0:', line) or re.match(r'\s*-:\s*0:\s*Source', line)]
                    start = max(0, int(line) - show_context)
                    end = min(len(lines), int(line) + show_context + 1)
                    context = "\n".join(lines[start:end])
                    # join overlapping contexts
                    if len(uncovered) > 0 and uncovered[-1][1] >= start and uncovered[-1][1] <= end:
                        start = max(uncovered[-1][1] - show_context, 0)
                        context = "\n".join(lines[start:end])
                        uncovered[-1] = (file, uncovered[-1][1], code, context if show_context > 0 else None)
                        continue
                uncovered.append((file, int(line), code, context if show_context > 0 else None))
        

    # Return the coverage
    return res.stdout.decode('utf-8'), uncovered

def cmake_build(path, cwd=None):
    if cwd is None:
        # Create a temporary directory
        cwd = tempfile.mkdtemp()
    if not exists(cwd):
        os.makedirs(cwd)

    # Compile the program
    subprocess.check_call(['cmake', path], cwd=cwd)
    subprocess.check_call(['make'], cwd=cwd)

def create_shared_lib(files, cwd=None):
    if cwd is None:
        # Create a temporary directory
        cwd = tempfile.mkdtemp()
    if not exists(cwd):
        os.makedirs(cwd)
    
    # Compile a shared object
    subprocess.check_call(['cc', '-fPIC', '-shared', '-o', 'shared_lib.so', *files], cwd=cwd)
    
    # Load the shared object
    so = CDLL(join(cwd,"shared_lib.so"),)

    return so

class interactive_cmd:
    def __init__(self, cmd, cwd=None):
        self.cmd = cmd
        if cwd is None:
            # Create a temporary directory
            cwd = tempfile.mkdtemp()
        if not exists(cwd):
            os.makedirs(cwd)
        self.cwd = cwd
        self.process = None

    def __enter__(self):
        self.process = subprocess.Popen(self.cmd, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(join(self.cwd, 'stderr.txt'), 'wb'))
        return self

    def wait(self, timeout=None):
        self.process.wait(timeout=timeout)

    def write(self, data):
        self.process.stdin.write(f"{data}\n".encode('utf-8'))
        self.process.stdin.flush()
    
    def read(self):
        return self.process.stdout.readline().decode('utf-8')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.process.terminate()
        return_code = self.process.wait()
        assert return_code == 0

class interactive_program(interactive_cmd):
    def __init__(self, program, args, cwd=None):
        super().__init__(['valgrind','--error-exitcode=1','--leak-check=full','./program'] + args, cwd=cwd)

        # Compile the program
        subprocess.check_call(['g++', program, '-o', os.path.join(cwd, 'program')])
