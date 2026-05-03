import re

_DYNAMIC_VAR_RE = re.compile(r"\{\{\$(\w+)\}\}")

test_cases = [
    '{"name": "wharf random {{$randomInt}}"}',
    '{{$randomInt}}',
    '{"key": "value {{$randomInt}}"}',
]

for test in test_cases:
    result = _DYNAMIC_VAR_RE.sub(lambda m: f'REPLACED_{m.group(1)}', test)
    print(f'Input:  {test}')
    print(f'Output: {result}')
    print()