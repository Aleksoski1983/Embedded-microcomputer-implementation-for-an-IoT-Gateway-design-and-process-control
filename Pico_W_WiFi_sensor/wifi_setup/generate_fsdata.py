#!/usr/bin/env python3
"""
Generate fsdata.c from HTML files in fs/ directory
This replaces the Perl makefsdata script
"""
import os
import sys


def guess_content_type(path: str) -> str:
    path = path.lower()
    if path.endswith('.html') or path.endswith('.shtml'):
        return 'text/html'
    if path.endswith('.js'):
        return 'application/javascript'
    if path.endswith('.css'):
        return 'text/css'
    if path.endswith('.png'):
        return 'image/png'
    if path.endswith('.jpg') or path.endswith('.jpeg'):
        return 'image/jpeg'
    if path.endswith('.svg'):
        return 'image/svg+xml'
    if path.endswith('.ico'):
        return 'image/x-icon'
    return 'text/plain'


def build_http_header(path: str, content_len: int) -> bytes:
    # lwIP httpd can either generate headers or use pre-included headers.
    # Your build expects headers to be included, otherwise it panics.
    content_type = guess_content_type(path)
    header = (
        'HTTP/1.0 200 OK\r\n'
        'Server: lwIP\r\n'
        f'Content-Type: {content_type}\r\n'
        # Content-Length is optional for HTTP/1.0 + connection close,
        # but helps some browsers.
        f'Content-Length: {content_len}\r\n'
        '\r\n'
    )
    return header.encode('ascii')

def file_to_c_array(filename):
    """Convert a file to a C byte array"""
    with open(filename, 'rb') as f:
        data = f.read()
    
    # Get the path for the file structure
    path = '/' + os.path.basename(filename)
    
    # Convert path to byte array
    path_bytes = path.encode('ascii') + b'\x00'
    
    # Create C array name
    c_name = 'data_' + os.path.basename(filename).replace('.', '_').replace('-', '_')
    
    # Generate C code
    output = f'static const unsigned char {c_name}[] = {{\n'
    output += f'\t/* {path} */\n'
    
    # Add path
    output += '\t'
    for i, byte in enumerate(path_bytes):
        output += f'0x{byte:02x}, '
        if (i + 1) % 12 == 0:
            output += '\n\t'
    output += '\n'
    
    # Add HTTP header + file data (lwIP httpd expects this)
    header_bytes = build_http_header(path, len(data))
    file_bytes = header_bytes + data

    for i, byte in enumerate(file_bytes):
        if i % 12 == 0:
            output += '\t'
        output += f'0x{byte:02x}, '
        if (i + 1) % 12 == 0:
            output += '\n'
    
    output += '};\n\n'
    
    return c_name, len(path_bytes), output

def generate_fsdata():
    """Generate my_fsdata.c from fs/ directory"""
    fs_dir = 'fs'
    
    if not os.path.exists(fs_dir):
        print(f"Error: {fs_dir} directory not found")
        sys.exit(1)
    
    # Get all files
    files = []
    for filename in os.listdir(fs_dir):
        if filename.startswith('.'):
            continue
        filepath = os.path.join(fs_dir, filename)
        if os.path.isfile(filepath):
            files.append(filepath)
    
    files.sort()
    
    # Generate header
    output = '#include "lwip/apps/fs.h"\n'
    output += '#include "lwip/def.h"\n'
    output += '#include <stddef.h>\n\n'
    
    # Generate file data arrays
    file_info = []
    for filepath in files:
        c_name, path_len, code = file_to_c_array(filepath)
        output += code
        file_info.append((c_name, path_len, os.path.basename(filepath)))
    
    # Generate file structures
    prev_file = 'NULL'
    for i, (c_name, path_len, filename) in enumerate(reversed(file_info)):
        struct_name = f'file_{filename.replace(".", "_").replace("-", "_")}'
        output += f'const struct fsdata_file {struct_name}[] = {{'
        output += f'{{{prev_file}, {c_name}, {c_name} + {path_len}, '
        output += f'sizeof({c_name}) - {path_len}, '
        output += 'FS_FILE_FLAGS_HEADER_INCLUDED | FS_FILE_FLAGS_HEADER_PERSISTENT}};\n\n'
        prev_file = struct_name
    
    # Add root pointer
    output += f'#define FS_ROOT {prev_file}\n\n'
    output += f'#define FS_NUMFILES {len(files)}\n'
    
    # Write output
    with open('my_fsdata.c', 'w') as f:
        f.write(output)
    
    print(f'Generated my_fsdata.c with {len(files)} files')

if __name__ == '__main__':
    generate_fsdata()
