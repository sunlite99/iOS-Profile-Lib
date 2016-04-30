# coding: utf-8
import plistlib
import uuid
from datetime import datetime
from io import BytesIO

try:
    import Crypto
    Crypto_support = True
except ImportError:
    Crypto_support = False
    print 'No crypto support'

try:
    import biplist
    binary_support = True
except ImportError:
    binary_support = False
    print 'No binary support'

try:
    import PIL
    from PIL import Image
    imgsupport = True
except ImportError:
    imgsupport = False
    print('No PIL support')


# Defining Exceptions
class ParamInvalid(Exception):
    """Exception raised for invalid param type.

    Attributes:
        atrib -- paramater missing
    """

    def __init__(self, atrib, etype):
        self.atrib = atrib
        self.etype = etype

    def __str__(self):
        return 'Argument {!r} is wrong type, should be {!r}.'.format(self.atrib, self.etype)


def typehandle(value, argn, opt=True, rtype=str):
    """Handles verifying type checks

    :param value: The value to be checked
    :param argn: The name of the argument to pass if an exception occurs
    :param opt: Bool if the variable is optional
    :param rtype: Type that the value should be (Defaults to str/unicode)
    :return: Value if success, ParamInvalid if failed
    """
    if opt and value is None:
        return
    if rtype == str:
        rtype = (str, unicode)  # isinstance can take a tuple as the second parameter
    if isinstance(value, rtype):
        return value
    raise ParamInvalid(argn, rtype)


def strip(indict):
    """Strips keys with a value of None from a dict

    :param indict: Dictionary to be striped
    :return: Striped dictionary
    """
    return {k: v for k, v in indict.items() if v is not None}


def uid():
    return uuid.uuid4().urn[9:].upper()


class Config(object):
    def __init__(self, host, ident=uid(), domain='org', hdesc=None, hname=None, horg=None,
                 rdate=None):
        self.host = typehandle(host, 'host', False)
        self.domain = typehandle(domain, 'domain')
        self.hdesc = typehandle(hdesc, 'hdesc')
        self.hname = typehandle(hname, 'hname')
        self.horg = typehandle(horg, 'horg')
        self.rdate = rdate
        self.rdn = domain + '.' + host
        self.ident = self.rdn + '.' + ident


class Payloads(object):
    def __init__(self, config):
        # noinspection PyTypeChecker
        self.config = typehandle(config, 'comfig', False, Config)
        self.profile = []

    def font(self, font, ident=uid(), name=None, **kwargs):
        if not font:
            return
        ident = 'font.' + ident
        returns = {'PayloadType': 'com.apple.font',
                   'Font': plistlib.Data(font),
                   'Name': typehandle(name, 'name')}
        returns = self.common(returns, ident, kwargs)
        self.profile += [strip(returns)]

    def webclip(self, url, label, fullscreen=None, ident=uid(), icon=None,
                precomposed=True, removable=True, **kwargs):
        ident = 'webclip.' + ident
        returns = {'PayloadType': 'com.apple.webClip.managed',
                   'URL': url,
                   'Label': label,
                   'IsRemovable': removable,
                   'Precomposed': typehandle(precomposed, 'precomposed', rtype=bool),
                   'FullScreen': typehandle(fullscreen, 'fullscreen', rtype=bool)}
        if icon and imgsupport:
            img = Image.open(icon) if isinstance(icon, str) else icon
            data_buffer = BytesIO()
            img.save(data_buffer, 'PNG')
            icon_data = data_buffer.getvalue()
            returns['Icon'] = plistlib.Data(icon_data)
        returns = self.common(returns, ident, kwargs)
        self.profile += [strip(returns)]

    def vpn(self, vpntype, alltraffic=False):
        return

    def certificate(self, certtype, cert, filename=None, password=None, ident=uid(), **kwargs):
        if not cert or not certtype in ('root', 'pkcs1', 'pem', 'pkcs12'):
            return
        returns = {'PayloadType': 'com.apple.security.' + certtype,
                   'PayloadContent': plistlib.Data(cert),
                   'PayloadCertificateFilename': typehandle(filename, 'filename'),
                   'Password': typehandle(password, 'password')}
        returns = self.common(returns, ident, kwargs)
        self.profile += [strip(returns)]

    def wifi(self, ssid, hidden=False, encryption='Any', hotspot=False, autojoin=True,
             pw=None, ident=uid(), **kwargs):
        ident = 'wifi.' + ident
        returns = {'PayloadType': 'com.apple.wifi.managed',
                   'SSID_STR': typehandle(ssid, 'ssid', rtype=bool),
                   'HIDDEN_NETWORK': typehandle(hidden, 'hidden', rtype=bool),
                   'AutoJoin': typehandle(autojoin, 'autojoim', rtype=bool),
                   'Password': typehandle(pw, 'password')}
        if encryption in ('WEP', 'WPA', 'WPA2', 'Any', 'None'):
            returns['EncryptionType'] = encryption
        returns = self.common(returns, ident, kwargs)
        self.profile += [strip(returns)]

    def common(self, content, ident, horg=None, hname=None, hdesc=None, ver=1):
        content['PayloadIdentifier'] = self.config.ident + '.' + ident
        content['PayloadOrganization'] = typehandle(horg, 'horg', )
        content['PayloadDisplayName'] = typehandle(hname, 'hname')
        content['PayloadDescription'] = typehandle(hdesc, 'hdesc')
        content['title'] = self.config.ident + '.' + ident
        content['PayloadUUID'] = uid()
        content['PayloadVersion'] = ver
        return content


def strippayload(payloads):
    # remove title attribute from payloads
    for i in payloads.profile:
        i.pop('title', None)
    return payloads


def mkplist(pload):
    """Turns a Payloads object into a plist

    :param pload: The Payloads object
    :return: Dict representation of plist
    """
    p = strippayload(pload)
    returns = {'PayloadType': 'Configuration',
               'PayloadVersion': 1,
               'PayloadIdentifier': pload.config.ident,
               'PayloadUUID': uid(),
               'PayloadDescription': typehandle(pload.config.hdesc, 'hdesc'),
               'PayloadDisplayName': typehandle(pload.config.hname, 'hdesc'),
               'PayloadOrganization': typehandle(pload.config.horg, 'horg'),
               'PayloadContent': pload.profile}
    if pload.config.rdate:
        returns['RemovalDate'] = pload.config.rdate
    return returns
