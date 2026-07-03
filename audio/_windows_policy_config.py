"""COM IPolicyConfig bindings ported from Tidal Audio Switcher."""

from __future__ import annotations

import sys

if sys.platform != "win32":
    raise ImportError("IPolicyConfig is only available on Windows")

from ctypes import HRESULT, POINTER, c_void_p
from ctypes.wintypes import BOOL, DWORD, LPWSTR

from comtypes import COMMETHOD, GUID, IUnknown
from comtypes import CLSCTX_ALL, CoCreateInstance

CLSID_CPolicyConfigClient = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")

ROLE_CONSOLE = 0
ROLE_MULTIMEDIA = 1
ROLE_COMMUNICATIONS = 2

_POLICY_METHODS = (
    COMMETHOD(
        [],
        HRESULT,
        "GetMixFormat",
        (["in"], LPWSTR, "pszDeviceName"),
        (["out"], POINTER(c_void_p), "ppFormat"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "GetDeviceFormat",
        (["in"], LPWSTR, "pszDeviceName"),
        (["in"], BOOL, "bDefault"),
        (["out"], POINTER(c_void_p), "ppFormat"),
    ),
    COMMETHOD([], HRESULT, "ResetDeviceFormat", (["in"], LPWSTR, "pszDeviceName")),
    COMMETHOD(
        [],
        HRESULT,
        "SetDeviceFormat",
        (["in"], LPWSTR, "pszDeviceName"),
        (["in"], c_void_p, "pEndpointFormat"),
        (["in"], c_void_p, "mixFormat"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "GetProcessingPeriod",
        (["in"], LPWSTR, "pszDeviceName"),
        (["in"], BOOL, "bDefault"),
        (["out"], c_void_p, "pmftDefaultPeriod"),
        (["out"], c_void_p, "pmftMinimumPeriod"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "SetProcessingPeriod",
        (["in"], LPWSTR, "pszDeviceName"),
        (["in"], c_void_p, "pmftPeriod"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "GetShareMode",
        (["in"], LPWSTR, "pszDeviceName"),
        (["out"], c_void_p, "pMode"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "SetShareMode",
        (["in"], LPWSTR, "pszDeviceName"),
        (["in"], c_void_p, "mode"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "GetPropertyValue",
        (["in"], LPWSTR, "pszDeviceName"),
        (["in"], BOOL, "bFxStore"),
        (["in"], c_void_p, "key"),
        (["in"], c_void_p, "pv"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "SetPropertyValue",
        (["in"], LPWSTR, "pszDeviceName"),
        (["in"], BOOL, "bFxStore"),
        (["in"], c_void_p, "key"),
        (["in"], c_void_p, "pv"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "SetDefaultEndpoint",
        (["in"], LPWSTR, "pwstrDeviceId"),
        (["in"], DWORD, "role"),
    ),
    COMMETHOD(
        [],
        HRESULT,
        "SetEndpointVisibility",
        (["in"], LPWSTR, "pszDeviceName"),
        (["in"], BOOL, "bVisible"),
    ),
)


class IPolicyConfig(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
    _methods_ = _POLICY_METHODS


class IPolicyConfigVista(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{568b9108-44bf-40b4-9006-86afe5b5a620}")
    _methods_ = _POLICY_METHODS


class IPolicyConfig10(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID("{00000000-0000-0000-c000-000000000046}")
    _methods_ = _POLICY_METHODS


def create_policy_config():
    """Create PolicyConfig using the same direct cast order as Tidal."""
    for interface in (IPolicyConfig, IPolicyConfigVista, IPolicyConfig10):
        try:
            return CoCreateInstance(CLSID_CPolicyConfigClient, interface, CLSCTX_ALL)
        except OSError:
            continue
    raise OSError(
        "PolicyConfigClient does not expose IPolicyConfig, "
        "IPolicyConfigVista, or IPolicyConfig10."
    )


def set_default_endpoint_for_all_roles(policy, device_id: str) -> list[tuple[int, int]]:
    """Set default endpoint for console, multimedia, and communications roles."""
    results: list[tuple[int, int]] = []
    for role in (ROLE_CONSOLE, ROLE_MULTIMEDIA, ROLE_COMMUNICATIONS):
        hr = policy.SetDefaultEndpoint(device_id, role)
        results.append((role, hr))
    return results
