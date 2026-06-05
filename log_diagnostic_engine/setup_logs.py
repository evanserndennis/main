from datetime import datetime
from pathlib import Path
import random

#  Path variable and file creation variables
target_dir = Path(__file__).resolve().parent / 'raw_logs'
target_files = [
    'server_01.log',
    'server_02.log',
    'server_03.log',
    'server_04.log',
    'server_05.log'
    ]

#  Random logging variables
records_per_file = 100
lower_bound_record = 5000
upper_bound_record = lower_bound_record + records_per_file
status_options = ['SUCCESS', 'PENDING', 'FAILED']
status_weights = [0.85, 0.13, 0.02]
status_messages = {
    'SUCCESS': 'STATUS: ID {record_id} was SUCCESSFUL\n',
    'PENDING': 'STATUS: ID {record_id} is still PENDING\n',
    'FAILED': 'STATUS: ID {record_id} FAILED\n',
}

#  Verifying target directory exists
if not target_dir.exists():
    target_dir.mkdir()
    print(f'STATUS: Created file directory {target_dir.resolve()}')
else:
    print('STATUS: File directory already exists')

#  Verifying target files exists
if len(list(target_dir.glob('*.log'))) == len(target_files):
    print('STATUS: Log files already exists')
else:
    for file in target_files:
        with (target_dir / file).open(mode='w', encoding='utf-8') as open_file:
            open_file.write(f'STATUS LOG {datetime.now()}\n')
            for record_id in range(lower_bound_record, upper_bound_record):
                [record_status] = random.choices(status_options, weights=status_weights, k=1)
                open_file.write(status_messages[record_status].format(record_id=record_id))