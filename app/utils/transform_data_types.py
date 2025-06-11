'''
This module contains functions to transform data types from the CSV files to the correct types for the database.
'''


def transform_vm_data(row):
    '''
    Transform the data types from the CSV files to the correct types for the database.
    '''
    row['virtual_cpu_count'] = int(row['virtual_cpu_count'])
    row['memory_gb'] = float(row['memory_gb'])
    row['price_per_hour_usd'] = float(row['price_per_hour_usd'])
    row['gpu_count'] = int(row['gpu_count'])
    row['gpu_memory'] = float(row['gpu_memory'])
    row['provider_name'] = row['provider_name']
    row['os_type'] = row['os_type'].strip()
    row['region'] = row['region'].strip()

    return row