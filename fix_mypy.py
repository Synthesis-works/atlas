import os, glob, re

tools_dir = 'apps/backend/agent/tools'
files = glob.glob(os.path.join(tools_dir, '*.py'))

for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'def execute\(\s*self\s*,\s*db:\s*Session\s*,\s*(.*?)\*\*kwargs:\s*Any\s*\)\s*->\s*Any:'
    
    def repl(m):
        args_str = m.group(1).strip()
        if not args_str or args_str.endswith(',') == False:
            args_str += ','
            
        args = []
        for segment in args_str.split(','):
            segment = segment.strip()
            if not segment: continue
            # E.g. 'benchmark_id: str', 'title: str = ""'
            arg_name = segment.split(':')[0].split('=')[0].strip()
            args.append(arg_name)
        
        new_def = 'def execute(self, db: Session, **kwargs: Any) -> Any:\n'
        for arg in args:
            new_def += f'        {arg} = kwargs.get(\"{arg}\")\n'
            new_def += f'        if {arg} is None:\n'
            new_def += f'            raise ValueError(\"{arg} is required\")\n'
            
        return new_def

    new_content = re.sub(pattern, repl, content)
    if new_content != content:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Patched {os.path.basename(fpath)}')
