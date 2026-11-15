"""Shared explicit water rules and native GCOV dual-polarisation conversion."""
import numpy as np


def read_dual_sigma(file, parent, bbox, target, minimum_fraction=.5):
    from .science import native_window, read_window
    paths = {name: parent + '/' + name for name in ['HHHH', 'HVHV', 'rtcGammaToSigmaFactor', 'mask']}
    missing = [name for name, path in paths.items() if path not in file]
    if missing:
        raise ValueError('HH/HV method requires ' + ', '.join(missing) + '. Select GCOV with HH and HV plus its conversion factor and mask, or explicitly choose Single-channel.')
    native = {}
    transform = epsg = shape = None
    for name, path in paths.items():
        values, attributes, t, crs = native_window(file, path, bbox)
        if shape is not None and (values.shape != shape or t != transform or crs != epsg):
            raise ValueError('HH, HV, conversion factor and source mask must have identical native grids. No approximate conversion is used.')
        native[name] = values
        shape, transform, epsg = values.shape, t, crs
    hh, hv, factor, mask = [native[k] for k in paths]
    power_ok = np.isfinite(hh) & (hh > 0) & np.isfinite(hv) & (hv > 0)
    factor_ok = np.isfinite(factor) & (factor > 0)
    source_ok = np.isfinite(mask) & (mask != 0) & (mask != 255)
    exceptions = parent + '/inputDataExceptionMask'
    if exceptions in file:
        values, _, t, crs = native_window(file, exceptions, bbox)
        if values.shape != shape or t != transform or crs != epsg:
            raise ValueError('Input exception mask differs from the native HH/HV grid.')
        source_ok &= np.isfinite(values) & (values == 0)
    joint = power_ok & factor_ok & source_ok
    def screen(data, attributes, t, crs):
        if data.shape != shape or t != transform or crs != epsg:
            raise ValueError('HH/HV native grid changed during conversion.')
        screen.rejections = {'joint_invalid_power': ~power_ok, 'joint_invalid_factor': ~factor_ok, 'joint_source_mask': ~source_ok}
        screen.quality_values = {}
        screen.retain = []
        data *= factor
        data[~joint] = np.nan
        return data
    screen.minimum_fraction = minimum_fraction
    converted = {}
    for name in ['HHHH', 'HVHV']:
        converted[name], _ = read_window(file, paths[name], bbox, target, native_filter=screen)
    aux = {'water_hh_sigma_power': converted['HHHH'], 'water_hv_sigma_power': converted['HVHV'], 'water_joint_accepted_fraction': screen.aux['accepted_fraction']}
    manifest = {'adapter_version': '1', 'normalization': 'sigma0 = gamma0 * rtcGammaToSigmaFactor in native linear power before averaging', 'joint_native_valid_samples': int(joint.sum()), 'native_window_samples': int(joint.size), 'minimum_native_valid_fraction': float(minimum_fraction), 'exception_mask_applied': exceptions in file, 'required_paths': paths}
    return aux, manifest, list(paths.values()) + ([exceptions] if exceptions in file else [])


def change_metrics(water, common, area):
    gain = ~water[0] & water[-1] & common
    loss = water[0] & ~water[-1] & common
    return {'water_gain_km2': float(gain.sum() * area), 'water_loss_km2': float(loss.sum() * area), 'net_water_change_km2': float((gain.sum() - loss.sum()) * area)}


def joint_water_evidence(hh, hv, common, hh_threshold, hv_threshold, area):
    def classify(shift=0):
        return np.isfinite(hh) & np.isfinite(hv) & (hh < hh_threshold + shift) & (hv < hv_threshold + shift)
    water = classify()
    scenarios = [{'shift_db': shift, 'hh_threshold_db': hh_threshold + shift, 'hv_threshold_db': hv_threshold + shift, 'area_km2': [float((state & common).sum() * area) for state in classify(shift)]} for shift in [-2, -1, 0, 1, 2]]
    return water, scenarios, change_metrics(water, common, area)


def joint_grid_sensitivity(hh_power, hv_power, common, hh_threshold, hv_threshold, area):
    rows = []
    for factor in [1, 2, 4]:
        h, w = common.shape
        h, w = h // factor * factor, w // factor * factor
        if not h or not w:
            continue
        mask = common[:h, :w].reshape(h // factor, factor, w // factor, factor).all(axis=(1, 3))
        arrays = [a[:, :h, :w].reshape(len(a), h // factor, factor, w // factor, factor).mean(axis=(2, 4)) for a in [hh_power, hv_power]]
        hh, hv = [10 * np.log10(np.where(a > 0, a, np.nan)) for a in arrays]
        water = (hh < hh_threshold) & (hv < hv_threshold)
        rows.append({'factor': factor, 'common_area_km2': float(mask.sum() * factor ** 2 * area), 'area_km2': [float(state[mask].sum() * factor ** 2 * area) for state in water]})
    return rows
