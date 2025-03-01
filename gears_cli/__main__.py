import redis
import click
import json
import os
import zipfile
import io
import subprocess, sys

DATA_BIN_FINE_NAME = 'Data.bin'
META_DATA_FILE_NAME = 'MetaData.json'

class Colors(object):
    @staticmethod
    def Cyan(data):
        return '\033[36m' + data + '\033[0m'

    @staticmethod
    def Yellow(data):
        return '\033[33m' + data + '\033[0m'

    @staticmethod
    def Bold(data):
        return '\033[1m' + data + '\033[0m'

    @staticmethod
    def Bred(data):
        return '\033[31;1m' + data + '\033[0m'

    @staticmethod
    def Gray(data):
        return '\033[30;1m' + data + '\033[0m'

    @staticmethod
    def Lgray(data):
        return '\033[30;47m' + data + '\033[0m'

    @staticmethod
    def Blue(data):
        return '\033[34m' + data + '\033[0m'

    @staticmethod
    def Green(data):
        return '\033[32m' + data + '\033[0m'

@click.group()
def gears_cli():
    pass

def create_connection(host,
                      port,
                      password,
                      username=None,
                      decode_responses=True,
                      ssl = False,
                      ssl_password=None,
                      ssl_keyfile=None,
                      ssl_certfile=None,
                      ssl_verify_ca=True,
                      ssl_ca_certs=None):
    global args
    try:
        r = redis.Redis(host=host,
                        port=port,
                        password=password,
                        username=username,
                        decode_responses=decode_responses,
                        ssl=ssl,
                        ssl_password=ssl_password,
                        ssl_keyfile=ssl_keyfile,
                        ssl_certfile=ssl_certfile,
                        ssl_cert_reqs='required' if ssl_verify_ca else None,
                        ssl_ca_certs=ssl_ca_certs)
        r.ping()
    except Exception as e:
        print(Colors.Bred('Cannot connect to Redis. Aborting (%s)' % str(e)))
        exit(1)
    return r

def print_res(res, res_id):
    res = str(res)
    res_id = Colors.Bold('%d)' % res_id)
    try:
        jsonStr = json.dumps(res, indent=4, sort_keys=True)
        jsonStr = Colors.Bold(jsonStr)
        res = json.loads(res)
        print('%s\t%s' % (res_id, jsonStr))
        return
    except Exception as e:
        pass
    print('%s\t%s' % (res_id, Colors.Bold(res)))

@gears_cli.command(help='Install give requirements')
@click.option('--host', default='localhost', help='Redis host to connect to')
@click.option('--port', default=6379, type=int, help='Redis port to connect to')
@click.option('--user', default=None, help='Redis acl user')
@click.option('--password', default=None, help='Redis password')
@click.option('--ssl', default=False, type=bool, help='Use ssl')
@click.option('--ssl-password', help='Passphrase for ssl key')
@click.option('--ssl-keyfile', type=click.Path(), help='Path to ssl key file')
@click.option('--ssl-certfile', type=click.Path(),help='Path to ssl certificate file')
@click.option('--ssl-ca-certs', type=click.Path(), help='Path to ssl ca certificate file')
@click.option('--ssl-verify-ca', default=True, type=bool, help='Whether or not to us CA to verify certs')
@click.option('--requirements-file', default=None, help='Path to requirements.txt file')
@click.argument('requirements', nargs=-1, type=click.UNPROCESSED)
def install_requirements(host, port, user, password,
                         ssl, ssl_password, ssl_keyfile, ssl_certfile, ssl_ca_certs, ssl_verify_ca,
                         requirements_file, requirements):
    r = create_connection(host=host, port=port, username=user, password=password,
                          ssl=ssl, ssl_password=ssl_password, ssl_keyfile=ssl_keyfile, ssl_verify_ca=ssl_verify_ca,
                          ssl_certfile=ssl_certfile, ssl_ca_certs=ssl_ca_certs)

    requirements = list(requirements)

    if requirements_file is not None:
        with open(requirements_file, 'r') as f:
            reqs = [(el.strip()) for el in f.readlines()] 
            requirements += reqs

    try:
        _ = r.execute_command('RG.PYEXECUTE', 'log("installing requirements")', 'REQUIREMENTS', *requirements)
    except Exception as e:
        print(Colors.Bred("failed running gear function (%s)" % str(e)))
        exit(1)
    print(Colors.Green('Done'))

@gears_cli.command(help='Run gears function')
@click.option('--host', default='localhost', help='Redis host to connect to')
@click.option('--port', default=6379, type=int, help='Redis port to connect to')
@click.option('--user', default=None, help='Redis acl user')
@click.option('--password', default=None, help='Redis password')
@click.option('--ssl', default=False, type=bool, help='Use ssl')
@click.option('--ssl-password', help='Passphrase for ssl key')
@click.option('--ssl-keyfile', type=click.Path(), help='Path to ssl key file')
@click.option('--ssl-certfile', type=click.Path(), help='Path to ssl certificate file')
@click.option('--ssl-ca-certs', type=click.Path(), help='Path to ssl ca certificate file')
@click.option('--ssl-verify-ca', default=True, type=bool, help='Whether or not to us CA to verify certs')
@click.option('--requirements', default=None, help='Path to requirements.txt file')
@click.argument('filepath')
@click.argument('extra_args', nargs=-1, type=click.UNPROCESSED)
def run(host, port, user, password, requirements, 
        ssl, ssl_password, ssl_keyfile, ssl_certfile, ssl_ca_certs, ssl_verify_ca,
        filepath, extra_args):
    r = create_connection(host=host, port=port, username=user, password=password,
                          ssl=ssl, ssl_password=ssl_password, ssl_keyfile=ssl_keyfile, ssl_verify_ca=ssl_verify_ca,
                          ssl_certfile=ssl_certfile, ssl_ca_certs=ssl_ca_certs)

    extra_args = list(extra_args)
    if requirements is not None:
        extra_args.append('REQUIREMENTS')
        with open(requirements, 'r') as f:
            reqs = [(el.strip()) for el in f.readlines()] 
            extra_args += reqs

    with open(filepath, 'rt') as f:
        script = f.read()
    q = ['rg.pyexecute', script] + extra_args

    try:
        reply = r.execute_command(*q)
    except Exception as e:
        print(Colors.Bred("failed running gear function (%s)" % str(e)))
        exit(1)
    
    if reply == 'OK':
        print('OK')
    else:
        results, errors = reply
        print(Colors.Bold('Results'))
        print(Colors.Bold('-------'))
        for i in range(len(results)):
            print_res(results[i], i + 1)
        print('')
        if len(errors) > 0:
            print(Colors.Bred('Errors'))
            print(Colors.Bred('------'))
            for i in range(len(errors)):
                print(Colors.Bred('%d)\t%s' % (i + 1, str(errors[i]))))
            exit(1)

def decode_utf(d):
    if isinstance(d, bytes):
        return d.decode('utf-8')
    if isinstance(d, dict):
        return {decode_utf(k): decode_utf(v) for k, v in d.items()}
    if isinstance(d, list):
        return [decode_utf(x) for x in d]
    return d

def extract_metadata(meta_data_reply):
    meta_data = {}
    for i in range(0, len(meta_data_reply), 2):
        key = meta_data_reply[i].decode('utf-8')
        value = decode_utf(meta_data_reply[i + 1])
        meta_data[key] = value
    return meta_data


def export_single_req(r, req_name, save_directory, output_prefix):
    try:
        metaDataValues, setializedData = r.execute_command('RG.PYEXPORTREQ', req_name)
    except Exception as e:
        print(Colors.Bred("failed exporting requirement (%s)" % str(e)))
        exit(1)

    metaData = extract_metadata(metaDataValues)
    jsonMetaDataStr = json.dumps(metaData, indent=4, sort_keys=True)

    if output_prefix is None:
        fileName = "redisgears-requirement-v%s-%s-%s.zip" % (metaData['GearReqVersion'], os.path.basename(metaData['Name']), metaData['CompiledOs'])
    else:
        fileName = "%s-%s.zip" % (output_prefix, metaData['CompiledOs'])
    filePath = os.path.join(save_directory, fileName)
    filePath = os.path.abspath(filePath)

    if os.path.exists(filePath):
        print(Colors.Bred("File %s already exists" % filePath))
        exit(1)

    print(Colors.Cyan("Saving exported requirement into %s" % filePath))

    with zipfile.ZipFile(filePath, "a", zipfile.ZIP_DEFLATED, False) as zf:
        zf.writestr(META_DATA_FILE_NAME, jsonMetaDataStr)
        data = b''.join(setializedData)
        zf.writestr(DATA_BIN_FINE_NAME, data)

@gears_cli.command(help='Export requirements from RedisGears')
@click.option('--host', default='localhost', help='Redis host to connect to')
@click.option('--port', default=6379, type=int, help='Redis port to connect to')
@click.option('--user', default=None, help='Redis acl user')
@click.option('--password', default=None, help='Redis password')
@click.option('--ssl', default=False, type=bool, help='Use ssl')
@click.option('--ssl-password', help='Passphrase for ssl key')
@click.option('--ssl-keyfile', type=click.Path(), help='Path to ssl key file')
@click.option('--ssl-certfile', type=click.Path(), help='Path to ssl certificate file')
@click.option('--ssl-ca-certs', type=click.Path(), help='Path to ssl ca certificate file')
@click.option('--ssl-verify-ca', default=True, type=bool, help='Whether or not to us CA to verify certs')
@click.option('--save-directory', default='./', help='Directory for exported files')
@click.option('--output-prefix', default=None, help='Prefix for the requirement zip file')
@click.option('--registration-id', multiple=True, default=[], help='Regisrations ids to extract their requirements')
@click.option('--requirement', multiple=True, default=[], help='Requirement to export')
@click.option('--all', is_flag=True, default=False, help='Export all requirements')
def export_requirements(host, port, user, password, 
                        ssl, ssl_password, ssl_keyfile, ssl_certfile, ssl_ca_certs, ssl_verify_ca,
                        save_directory, output_prefix, registration_id, all, requirement):
    r = create_connection(host=host, port=port, username=user, password=password,
                          ssl=ssl, ssl_password=ssl_password, ssl_keyfile=ssl_keyfile,
                          ssl_certfile=ssl_certfile, ssl_ca_certs=ssl_ca_certs, ssl_verify_ca=ssl_verify_ca,
                          decode_responses=False)

    if all:
        all_reqs = r.execute_command('RG.PYDUMPREQS')
        if len(all_reqs) == 0:
            print(Colors.Bred("No requirements to export"))
            exit(1)
        for req in all_reqs:
            md = extract_metadata(req)
            export_single_req(r, md['Name'], save_directory, output_prefix)
        return

    requirements_to_export = set()

    if len(registration_id) > 0:
        registrations = r.execute_command('RG.DUMPREGISTRATIONS')
        for registration_id in registration_id:
            registration = [r for r in registrations if r[1].decode('utf-8') == registration_id]
            if len(registration) != 1:
                print(Colors.Bred("No such registration %s" % registration_id))
                exit(1)
            registration = registration[0]
            session = registration[9]
            session = eval(session.decode('utf-8'))
            [requirements_to_export.add(n['name']) for n in session['depsList']]

    for req in requirement:
        requirements_to_export.add(req)

    for req in requirements_to_export:
        export_single_req(r, req, save_directory, output_prefix)

def import_single_req(r, req_io, bulk_size_in_bytes):
    with zipfile.ZipFile(req_io, "r", zipfile.ZIP_DEFLATED, False) as zf:
        try:
            data = zf.read(DATA_BIN_FINE_NAME)
        except Exception as e:
            print(Colors.Bred("Bad zip format (%s)" % str(e)))
            exit(1)
        data = [data[i : i + bulk_size_in_bytes] for i in range(0, len(data), bulk_size_in_bytes)]
        try:
            _ = r.execute_command('RG.PYIMPORTREQ', *data)
        except Exception as e:
            print(Colors.Bred("failed import requirement (%s)" % str(e)))
            exit(1)

    
@gears_cli.command(help='Import requirements to RedisGears')
@click.option('--host', default='localhost', help='Redis host to connect to')
@click.option('--port', default=6379, type=int, help='Redis port to connect to')
@click.option('--user', default=None, help='Redis acl user')
@click.option('--password', default=None, help='Redis password')
@click.option('--ssl', default=False, type=bool, help='Use ssl')
@click.option('--ssl-password', help='Passphrase for ssl key')
@click.option('--ssl-keyfile', type=click.Path(), help='Path to ssl key file')
@click.option('--ssl-certfile', type=click.Path(), help='Path to ssl certificate file')
@click.option('--ssl-ca-certs', type=click.Path(), help='Path to ssl ca certificate file')
@click.option('--ssl-verify-ca', default=True, type=bool, help='Whether or not to us CA to verify certs')
@click.option('--requirements-path', default='./', help='Path of requirements directory containing requirements zip files, could also be a zip file contains more requirements zip files')
@click.option('--all', is_flag=True, default=False, help='Import all requirements in zip file')
@click.option('--bulk-size', default=10, type=int, help='Max bulk size to send to redis in MB')
@click.argument('requirements', nargs=-1, type=click.UNPROCESSED)
def import_requirements(host, port, user, password, 
                        ssl, ssl_password, ssl_keyfile, ssl_certfile, ssl_ca_certs, ssl_verify_ca,
                        requirements_path, all, bulk_size, requirements):
    def install_req(req):
        try:
            req_data = zf.read(req)
        except Exception as e:
            print(Colors.Bred("Requirement %s could not be found in zip, error='%s'" % (req, str(e))))
            exit(1)
        io_buffer = io.BytesIO(req_data)
        import_single_req(r, io_buffer, bulk_size_in_bytes)
        print(Colors.Green('Requirement %s imported successfully' % req))

    r = create_connection(host=host, port=port, username=user, password=password,
                          ssl=ssl, ssl_password=ssl_password, ssl_keyfile=ssl_keyfile,
                          ssl_certfile=ssl_certfile, ssl_ca_certs=ssl_ca_certs, ssl_verify_ca=ssl_verify_ca,
                          decode_responses=False)

    bulk_size_in_bytes = bulk_size * 1024 * 1024

    if len(requirements) == 0 and not all:
        print(Colors.Bold('Warngin: no requirements specified'))

    requirements_path = os.path.abspath(requirements_path)

    if not os.path.exists(requirements_path):
        print(Colors.Bred("File %s does not exists" % requirements_path))
        exit(1)

    if requirements_path.endswith('.zip'):
        if len(requirements) == 0:
            all = True
        with zipfile.ZipFile(requirements_path, "r", zipfile.ZIP_DEFLATED, False) as zf:
            if all:
                for req in zf.namelist():
                    install_req(req)
            else:
                for req in requirements:
                    install_req(req)
        return

    if not os.path.isdir(requirements_path):
        print(Colors.Bred("%s is not a directory" % requirements_path))
        exit(1)

    for req in requirements:
        req_path = os.path.join(requirements_path, req)
        if not os.path.exists(req_path):
            print(Colors.Bred("File %s does not exists" % req_path))
            exit(1)
        import_single_req(r, req_path, bulk_size_in_bytes)
        print(Colors.Green('Requirement %s imported successfully' % req_path))

@gears_cli.command(help='delete all registered gears')
@click.option('--host', default='localhost', help='Redis host to connect to')
@click.option('--port', default=6379, type=int, help='Redis port to connect to')
@click.option('--user', default=None, help='Redis acl user')
@click.option('--password', default=None, help='Redis password')
def delete_all_gears(host, port, user, password):  
    r = create_connection(host=host, port=port, username=user, password=password)
    regs = r.execute_command('RG.DUMPREGISTRATIONS')
    for reg in regs:
        # get the id of the registration
        r.execute_command('RG.UNREGISTER', reg[1])
        print("deleting registration id: {}".format(reg[1]))

@gears_cli.command(help='list all registered gears')
@click.option('--host', default='localhost', help='Redis host to connect to')
@click.option('--port', default=6379, type=int, help='Redis port to connect to')
@click.option('--user', default=None, help='Redis acl user')
@click.option('--password', default=None, help='Redis password')
def list_all_gears(host, port, user, password):  
    r = create_connection(host=host, port=port, username=user, password=password)
    regs = r.execute_command('RG.DUMPREGISTRATIONS')
    for reg in regs:
        print("{}\n".format(reg))

@gears_cli.command(help="""\b
monitor-stream - 
   STREAM_NAME must not match any data in the stream 
   example stream-name regular expression: xadd.*camera:0:videoinput
      note the xadd helps to differentiate between writes and reads of key
   """)
@click.option('--host', default='localhost', help='Redis host to connect to')
@click.option('--port', default=6379, type=int, help='Redis port to connect to')
@click.option('--user', default=None, help='Redis acl user')
@click.option('--password', default=None, help='Redis password')
@click.argument('stream_regex')
@click.argument('stream_name')
def monitor_stream(host, port, user, password, stream_regex, stream_name):  
    cmd = "redis-cli -h {} -p {} monitor | grep -i '{}' | pv -lf --name {} | grep {}".format(host, port, stream_regex, stream_name, stream_name)
    print(cmd) 
    p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE)

    while True:
        out = p.stderr.read(1)
        if out == '' and p.poll() != None:
            break
        if out != '':
            out = out.decode()
            sys.stderr.write(out)
	
@gears_cli.command(help='watch a gear file for changes and update engine as needed')
@click.option('--host', default='localhost', help='Redis host to connect to')
@click.option('--port', default=6379, type=int, help='Redis port to connect to')
@click.option('--user', default=None, help='Redis acl user')
@click.option('--password', default=None, help='Redis password')
@click.argument('gear_filename')
def watch(host, port, user, password, gear_filename):  
    cmd = "watchexec -w {} 'gears-cli --host {} --port {} delete-all-gears && gears-cli run {}'".format(host, port, gear_filename, gear_filename)
    print(cmd) 
    p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE)
    print("press ctrl-c to exit")
    while True:
        out = p.stderr.read(1)
        if out == '' and p.poll() != None:
            break
        if out != '':
            sys.stdout.write(out)
            sys.stderr.write(out)

def main():
    gears_cli()

if __name__ == '__main__':
    gears_cli()
