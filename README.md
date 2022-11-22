# C_testing_framework
python pytest based framework to check C/C++ memory management and functional behavior
## setup
* initialize virtual enviornment:
```[bash]
virtualenv env
source env/bin/activate
```
* install all required packages:
```[bash]
pip install -r requirements.txt
```
* configure project directory
## run tests
in order to run all tests type:
```[bash]
pytest
```
in order to run tests in specific file run:
```[bash]
pytest <test_file.py>
```
in order to run specific test function in specific file run:
```[bash]
pytest <test_file.py>::<test_function>
```
