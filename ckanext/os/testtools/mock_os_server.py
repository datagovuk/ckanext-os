import logging
from xmlrpclib import Fault

import paste.script
from paste.util.multidict import MultiDict

# NB Mock drupal details must match those in ckanext-dgu/test-core.ini
MOCK_OS_SERVER_PORT = 8051
MOCK_OS_SERVER_HOST = 'localhost'
MOCK_OS_SERVER_HOST_AND_PORT = '%s:%s' % (MOCK_OS_SERVER_HOST,
                                          MOCK_OS_SERVER_PORT)
MOCK_API_KEY = 'testapikey'

def get_mock_os_server_config():
    return {
        'http_host': 'localhost',
        'http_port': MOCK_OS_SERVER_PORT,
        }

class Command(paste.script.command.Command):
    '''Mock OS Server commands

    mock_os_server run OPTIONS
    '''
    parser = paste.script.command.Command.standard_parser(verbose=True)
    default_verbosity = 1
    group_name = 'ckanext-os'
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 1
    max_args = None
    parser.add_option('-q', '--quiet',
                      dest='is_quiet',
                      action='store_true',
                      default=False,
                      help='Quiet mode')

    def command(self):
        cmd = self.args[0]
        if cmd == 'run':
            server_process = MockOsServerProcess()
            if not self.options.is_quiet:
                server_process.log.setLevel(logging.DEBUG)
                formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                handler = logging.StreamHandler()
                handler.setFormatter(formatter)
                server_process.log.addHandler(handler)
            server_process.run()

class MockOsServerProcess(object):
    def __init__(self):
        self.log = logging.getLogger(__name__)
        
    def run(self):
        import SimpleHTTPServer
        import SocketServer
        from BaseHTTPServer import BaseHTTPRequestHandler

        config = get_mock_os_server_config()

        # Server
        class MockOsServer(BaseHTTPRequestHandler):
            def parse_path(self):
                # parse path and parameters
                path = self.path.split('?')[0]
                params = self.path[len(path)+1:].split('&')
                param_dict = MultiDict()
                for param in params:
                    key = param.split('=')[0]
                    value = param[len(key)+1:]
                    param_dict.add(key, value)
                return path, param_dict
                
            def do_GET(self):
                path, param_dict = self.parse_path()
                    
                # 'http://%s/InspireGaz/gazetteer?q=%s'
                if path == '/InspireGaz/gazetteer':
                    return self.gazetteer(param_dict)

                # 'http://%s/InspireGaz/postcode?q=%s'
                elif path == '/InspireGaz/postcode':
                    return self.postcode(param_dict)

                elif path == '/':
                    self.send_response(200)
                    self.wfile.write('Mock OS Server')
                    return

                self.send_error(404)

            def do_POST(self):
                path, param_dict = self.parse_path()
                #data = 

                if 'apikey' not in param_dict or \
                   param_dict['apikey'] != MOCK_API_KEY:
                    self.send_error(403)
                
                # 'http://%s/geoserver/wfs'
                if path == '/geoserver/wfs':
                    return self.admin_boundaries()
                self.send_error(404)

            def gazetteer(self, param_dict):
                q = param_dict.get('q')
                message = '''<?xml version="1.0" encoding="UTF-8"?>
  <GazetteerResultVO>
    <items>
      <GazetteerItemVO>
        <county>Greater London Authority</county>
        <easting>-0.13447746307679012</easting>
        <name>Greater London Authority</name>
        <northing>51.48962984909882</northing>
        <point>-0.13447746307679012 51.48962984909882</point>
        <type>BOUNDARY</type>
        <zoomtype>3</zoomtype>
      </GazetteerItemVO>
    </items>
  </GazetteerResultVO>
'''
                if not q:
                    message = '''<?xml version="1.0" encoding="UTF-8"?>
  <GazetteerResultVO>
    <items/>
  </GazetteerResultVO>
'''
                self.send_response(200)
                self.send_header('Content-Type', 'application/xml')
                self.end_headers()
                self.wfile.write(message)

            def postcode(self, param_dict):
                q = param_dict.get('q')
                # EH99+1SP
                message = '''<?xml version="1.0" encoding="UTF-8"?>
  <CodePointItemVO>
    <easting>-3.174923783029438</easting>
    <northing>55.951956905012295</northing>
    <point>-3.174923783029438 55.951956905012295</point>
  </CodePointItemVO>
'''
                if q in ('DL3+0UR', 'DL3%200UR'):
                    message = '''<?xml version="1.0" encoding="UTF-8"?>
  <CodePointItemVO>
    <easting>-1.5719322177872677</easting>
    <northing>54.55246821308707</northing>
    <point>-1.5719322177872677 54.55246821308707</point>
  </CodePointItemVO>
'''
                if not q:
                    message = '''<?xml version="1.0" encoding="UTF-8"?>
  <CodePointItemVO>
    <easting/>
    <northing/>
    <point> </point>
  </CodePointItemVO>
'''
                if q in ('SO16+0AS', 'SO16%200AS'):
                    message = '''<?xml version="1.0" encoding="UTF-8"?>
  <EmptyCodePointItemVO>
    <easting/>
    <northing/>
    <point>null null</point>
  </EmptyCodePointItemVO>
'''
                self.send_response(200)
                self.send_header('Content-Type', 'application/xml')
                self.end_headers()
                self.wfile.write(message)

            def admin_boundaries(self):
                message = '''{"type":"FeatureCollection","features":[{"type":"Feature","id":"UK_Admin_Boundaries_250m_4258.fid-4d34146c_1364e13b29d_-4f42","geometry":{"type":"MultiPolygon","coordinates":[[[[-4.543907032992606,50.9447173620452],[-4.546951552891223,50.95269509014119],[-4.535536997267976,50.96559909154817],[-2.954281938979178,50.82121599008027]]]},"geometry_name":"the_geom","properties":{"NAME":"Wrecsam - Wrexham"}}],"crs":{"type":"EPSG","properties":{"code":"4258"}},"bbox":[-5.3532518686055415,50.201508698391706,0.356977049661522,53.61635012856053]}'''
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(message)
        
        # Create server
        server = SocketServer.TCPServer((config['http_host'],
                                        config['http_port']),
                                       MockOsServer)

        # Run the server's main loop
        self.log.debug('Serving on http://%s:%s',
                      config['http_host'], config['http_port'])
        server.serve_forever()

