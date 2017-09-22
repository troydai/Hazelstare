import sys
import os.path
import json
import re

import pylint.lint


class OutputToFile(object):
    def __init__(self, file_path):
        self.original_stdout = None
        self.file_path = file_path
        self.file_desc = None

    def __enter__(self):
        self.original_stdout = sys.stdout
        self.file_desc = open(self.file_path, 'w')
        sys.stdout = self.file_desc

        return self.file_desc
    
    def __exit__(self, *args):
        self.file_desc.close()
        sys.stdout = self.original_stdout


def generate_report():
    work_dir = os.getcwd()
    src_dir = os.path.join(work_dir, 'src')
    if not os.path.isdir(src_dir):
        src_dir = work_dir

    rc_file = os.path.join(work_dir, 'pylintrc')
    if not os.path.isfile(rc_file):
        rc_file = None
    
    # find all setup.py
    modules = [next(dir for dir, _, file_in_root in os.walk(root) if '__init__.py' in file_in_root)
               for root, _, files in os.walk(src_dir) if 'setup.py' in files]

    with OutputToFile('pylint_result.json'):
        pylint.lint.Run([*modules, '--rcfile', rc_file], exit=False)


def update_files(report_file, *args):
    print('Useless suppressions to remove: {}'.format(', '.join(args)))
    with open(report_file, 'r') as f:
        results = [r for r in json.load(f) if r['symbol'] == 'useless-suppression']

    clue = re.compile("#(\s)*pylint:(\s)*disable(\s)*=(\s)*")
    to_remove = set(args)
    
    for r in [r for r in results if any(s for s in to_remove if s in r['message'])]:
        line_number = r['line'] - 1
        filepath = r['path']
        print(filepath)
        with open(filepath, 'r') as f:
            content = f.readlines()
            line_content = content[line_number]
            match = clue.search(line_content)

            if not match:
                print('ERROR: ' + line_content)
                break

            suppresed = set(each.strip() for each in line_content[match.end():].strip().split(','))
            remaining = suppresed - to_remove

            if not any(remaining):
                line_content = line_content[:match.start()].rstrip() + line_content[len(line_content) - 1]
                content[line_number] = line_content
            else:
                line_content = line_content[:match.start()].rstrip() + \
                               '  # pylint: disable={}'.format(','.join(remaining)) + \
                               line_content[len(line_content) - 1]

        with open(filepath, 'w') as f:
            f.writelines(content)
        
        

if __name__ == '__main__':
    existing_report = os.path.join(os.getcwd(), 'pylint_result.json')
    if not os.path.exists(existing_report):
        generate_report()
    
    update_files(existing_report, 'line-too-long', 'too-few-public-methods')
