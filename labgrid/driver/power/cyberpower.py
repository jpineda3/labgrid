
# labgrid/driver/power/cyberpower.py
# Backend for NetworkPowerDriver to control CyberPower ePDU via SNMPv1.

from pysnmp.hlapi import (
    SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity,
    getCmd, setCmd
)

# Labgrid will inspect PORT for proxymanager logic; SNMP uses UDP/161
PORT = 161

# CyberPower MIB v2.11 OIDs for outlet state and commands:
# Status: ePDUOutletStatusOutletState.<outlet> (1=on, 2=off)
STATUS_OID_PREFIX = '1.3.6.1.4.1.3808.1.1.3.3.5.1.1.4'
# Control: ePDUOutletControlOutletCommand.<outlet> (1=on, 2=off, etc.)
CTRL_OID_PREFIX   = '1.3.6.1.4.1.3808.1.1.3.3.3.1.1.4'

# Immediate command values
IMMEDIATE_ON  = 1
IMMEDIATE_OFF = 2

def _community():
    # Adjust to your site defaults; SNMPv1 uses community strings
    return {'read': 'public', 'write': 'private'}

def _get_v1(host: str, oid: str):
    """SNMPv1 GET -> int value."""
    engine = SnmpEngine()
    comm   = CommunityData(_community()['read'], mpModel=0)  # SNMPv1
    trans  = UdpTransportTarget((host, PORT), timeout=1, retries=3)
    ctx    = ContextData()
    errorIndication, errorStatus, errorIndex, varBinds = next(getCmd(
        engine, comm, trans, ctx, ObjectType(ObjectIdentity(oid))
    ))
    if errorIndication or errorStatus:
        raise RuntimeError(f"SNMPv1 get failed: {errorIndication or errorStatus.prettyPrint()}")
    return int(varBinds[0][1])

def _set_v1(host: str, oid: str, value: int):
    """SNMPv1 SET with integer command."""
    engine = SnmpEngine()
    comm   = CommunityData(_community()['write'], mpModel=0)  # SNMPv1
    trans  = UdpTransportTarget((host, PORT), timeout=2, retries=3)
    ctx    = ContextData()
    errorIndication, errorStatus, errorIndex, varBinds = next(setCmd(
        engine, comm, trans, ctx, ObjectType(ObjectIdentity(oid), value)
    ))
    if errorIndication or errorStatus:
        raise RuntimeError(f"SNMPv1 set failed: {errorIndication or errorStatus.prettyPrint()}")

def power_set(host, port, index, value: bool):
    """
    Called by labgrid's NetworkPowerDriver.
    value=True -> ON, False -> OFF.
    """
    cmd = IMMEDIATE_ON if value else IMMEDIATE_OFF
    oid = f"{CTRL_OID_PREFIX}.{int(index)}"
    _set_v1(host, oid, cmd)

def power_get(host, port, index):
    """
    Called by labgrid's NetworkPowerDriver.
    Returns True if the outlet reports 'on' (1), False if 'off' (2).
    """
    oid = f"{STATUS_OID_PREFIX}.{int(index)}"
    state = _get_v1(host, oid)
    if state == 1:
        return True
    if state == 2:
        return False
    # Any other value -> unknown; default to False
    return False
