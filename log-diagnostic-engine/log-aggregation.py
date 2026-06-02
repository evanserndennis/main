from pathlib import Path

#  Initializing variables
target_files = Path(__file__).resolve().parent / 'raw_logs'
system_metrics = {
    'files_processed': 0,
    'records_processed': 0,
    'status_counts': {
        'SUCCESS': 0,
        'PENDING': 0,
        'FAILED': 0
    },
    'skipped_records': 0
}

#  Aggregating log entries
if target_files.exists():
    for file in target_files.glob('*.log'):
        with file.open(mode='r', encoding='utf-8') as open_file:
            system_metrics['files_processed'] += 1
            for line in open_file:
                try:
                    if line.startswith('STATUS LOG'):
                        continue
                    else:
                        system_metrics['records_processed'] += 1
                        for status in system_metrics['status_counts']:
                            if status in line:
                                system_metrics['status_counts'][status] += 1
                                break
                        else:
                            raise ValueError('Malformed data line encoutnered')
                except ValueError:
                    system_metrics['skipped_records'] += 1

print(
    f'''
    ========================= SYSTEM METRICS REPORT =========================
    
    Total files processed: {system_metrics['files_processed']} files

    Total records processed: {system_metrics['records_processed']} records
    
    Record breakdown:
        └─ SUCCESS: {system_metrics['status_counts']['SUCCESS']} records
        └─ PENDING: {system_metrics['status_counts']['PENDING']} records
        └─ FAILED: {system_metrics['status_counts']['FAILED']} records
    
    Malformed rows skipped: {system_metrics['skipped_records']} records
    
    =========================================================================
    '''
)