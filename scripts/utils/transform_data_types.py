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


def transform_storage_data(row):
    '''
    Transform the data types from storage CSV files to the correct types for the database.
    '''
    # Convert numeric fields, handling empty strings and None values
    def safe_float_convert(value):
        if value is None or value == '' or value == 'None':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    row['capacity_price'] = safe_float_convert(row.get('capacity_price'))
    row['read_price'] = safe_float_convert(row.get('read_price'))
    row['write_price'] = safe_float_convert(row.get('write_price'))
    row['flat_item_price'] = safe_float_convert(row.get('flat_item_price'))
    
    # Ensure string fields are properly trimmed
    row['provider_name'] = row['provider_name'].strip() if row['provider_name'] else ''
    row['service_name'] = row['service_name'].strip() if row['service_name'] else ''
    row['storage_class'] = row['storage_class'].strip() if row['storage_class'] else ''
    row['region'] = row['region'].strip() if row['region'] else ''
    row['access_tier'] = row['access_tier'].strip() if row['access_tier'] else ''

    return row