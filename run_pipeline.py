"""BHT Dashboard Update Pipeline
Run this script to update the dashboard after exporting new Lingxing reports to Desktop.
Output: Weekly_Dashboard.html on Desktop (the only file you need)
"""
import subprocess, os, sys

DATA_DIR = os.path.join(os.path.expanduser("~"), "bht_data")
os.chdir(DATA_DIR)

steps = [
    (['python3', 'gen_weekly.py'], 'Step 1/4: Extract weekly data'),
    (['python3', 'process_data.py'], 'Step 2/4: Merge Lingxing reports'),
    (['python3', 'gen_prev_months.py'], 'Step 3/4: Fill missing months from weekly data'),
    (['python3', 'build_html.py'], 'Step 4/4: Build dashboard HTML'),
]

for cmd, desc in steps:
    print(f'\n{"="*50}')
    print(desc)
    print(f'{"="*50}')
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f'ERROR:', result.stderr)
        sys.exit(1)

print(f'\n{"="*50}')
print('Done! Open C:/Users/haishan10/Desktop/Weekly_Dashboard.html')
print(f'{"="*50}')
