import numpy as np
import struct
import array
import os
from dopamineAnalysis import DopamineData


# Чтение файла
def readDAdata(f):
    dopamineData = DopamineData()

    byte_data = f.read()

    data_length = (1024 * 2 + 8 + 8)  # length of file in bytes
    num_of_chunks = len(byte_data) // data_length  # number of chunks of data

    for i in range(num_of_chunks):
        # First triangle (500 x int16 = 1000 bytes)
        first_triangle = struct.unpack("h"*500, byte_data[0 + i*data_length : 1000 + i*data_length])
        # Second trianle (1000 bytes)
        second_triangle = struct.unpack("h"*500, byte_data[1000 + i*data_length : 2000 + i*data_length])
        # Additional data (24 bytes)
        additional_data = struct.unpack("h"*24, byte_data[2000 + i*data_length : 2048 + i*data_length])
        # Time (int64 = 8 byte)
        package_time = struct.unpack("Q", byte_data[2048 + i*data_length : 2056 + i*data_length])[0]
        # Errors (UINT8, but it is actually 64 bytes??????????)
        err_info = struct.unpack("Q", byte_data[2056 + i*data_length : 2064 + i*data_length])

        # Adding to class
        dopamineData.add_data(package_time, first_triangle, second_triangle, additional_data, err_info)

    if dopamineData.first_peaks == {}:
        raise Exception('File was not parsed correctly')


    return dopamineData
    # from 469 to 1201941 => 1201472 per 20 minutes => 20*60/1201472 => package each ~0.001 sec => package each ~1msec
