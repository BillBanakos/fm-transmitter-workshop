#!/usr/bin/env python3
"""
fm_fft.py - prove an FM transmitter simulation really does FM.

Reads an LTspice .raw file, resamples the (non-uniform) transient data onto a
uniform grid, takes a Blackman-windowed FFT of the steady-state part, then fits
the sideband amplitudes around the carrier to Bessel functions |J_k(beta)|.

It prints the carrier frequency, the modulation index beta, the peak deviation
and Carson bandwidth, and plots the full spectrum plus a zoom around the
carrier with the fitted Bessel lines on top. If the red markers sit on the FFT
lines, the output is FM (not AM, not harmonics).

    python fm_fft.py "fm transmitter_only_vco.raw" --node "V(vout)"
    python fm_fft.py sim.raw --node "v(vout)" --dialect ngspice
    python fm_fft.py --demo            # synthetic FM signal, no LTspice needed

Tip: set the audio source so beta ~= 2.405 - the carrier then disappears, which
is an unambiguous visual proof of FM.
"""
import argparse
import sys

import numpy as np
from scipy.special import jv


def load_raw(path, node, dialect=None):
    from spicelib import RawRead
    r = RawRead(path, dialect=dialect) if dialect else RawRead(path)
    t = np.abs(np.asarray(r.get_trace("time").get_wave(), dtype=float))  # LTspice may store sign-flipped times
    v = np.real(np.asarray(r.get_trace(node).get_wave()))
    return t, v


def demo_signal(fc=100e6, fm=20e3, beta=2.405, t_end=270e-6, seed=0):
    """FM carrier + 2nd harmonic on a jittered (LTspice-like) time grid."""
    rng = np.random.default_rng(seed)
    dt = 1 / (40 * fc)
    t = np.cumsum(dt * (0.5 + rng.random(int(t_end / dt))))
    t = t[t < t_end]
    ph = 2 * np.pi * fc * t + beta * np.sin(2 * np.pi * fm * t)
    v = np.cos(ph) + 0.05 * np.cos(2 * ph)
    return t, v


def analyse(t, v, t0, t1, fs, fm, span, K=8):
    if t[-1] < t1:
        sys.exit(f"simulation ends at {t[-1]*1e6:.1f} us, before --t1 = {t1*1e6:.1f} us")
    tu = np.arange(t0, t1, 1 / fs)
    x = np.interp(tu, t, v)
    x -= x.mean()

    w = np.blackman(len(x))
    nfft = 1 << (int(np.ceil(np.log2(len(x)))) + 2)
    X = np.fft.rfft(x * w, nfft)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    mag = 2 * np.abs(X) / w.sum()  # sine amplitude [V]

    # carrier: power centroid around the strongest bin
    ipk = int(np.argmax(mag))
    band = np.abs(f - f[ipk]) < span
    fc = np.sum(f[band] * mag[band] ** 2) / np.sum(mag[band] ** 2)

    # line amplitudes at fc + k*fm (local max within +-fm/4)
    k = np.arange(-K, K + 1)
    lines = np.array([mag[np.abs(f - (fc + kk * fm)) < fm / 4].max() for kk in k])
    c = lines / np.sqrt(np.sum(lines ** 2))  # power-normalised

    # fit beta: coarse grid (avoids local minima), then refine
    err = lambda b: np.sum((c - np.abs(jv(k, b))) ** 2)
    grid = np.linspace(0.01, K - 1, 2000)
    b0 = grid[np.argmin([err(b) for b in grid])]
    fine = np.linspace(max(b0 - 0.01, 0.0), b0 + 0.01, 2001)
    beta = fine[np.argmin([err(b) for b in fine])]
    return dict(f=f, mag=mag, fc=fc, k=k, lines=lines, c=c, beta=beta)


def report(r, fm):
    fc, beta, k, c = r["fc"], r["beta"], r["k"], r["c"]
    print(f"f_c      = {fc/1e6:.4f} MHz")
    print(f"beta     = {beta:.3f}   ->  peak deviation = {beta*fm/1e3:.1f} kHz")
    print(f"Carson   = {2*(beta+1)*fm/1e3:.1f} kHz")
    print(f"Td demod = 1/(4 f_c) = {1/(4*fc)*1e9:.4f} ns")
    print("\n  k   meas[dB]  |J_k(beta)|[dB]")
    for kk, ci in zip(k, c):
        print(f"{kk:+3d}  {20*np.log10(ci+1e-12):8.1f}  {20*np.log10(abs(jv(kk, beta))+1e-12):8.1f}")


def plot(r, node, fm, span, save=None, show=True):
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    f, mag, fc, k, lines, beta = r["f"], r["mag"], r["fc"], r["k"], r["lines"], r["beta"]
    dB = 20 * np.log10(mag + 1e-15)
    fig, ax = plt.subplots(2, 1, figsize=(11, 7))
    ax[0].plot(f / 1e6, dB, lw=0.7)
    ax[0].set_xlim(0, 4 * fc / 1e6)
    ax[0].set_ylim(dB.max() - 100, dB.max() + 5)
    ax[0].set_title(f"{node}: full spectrum (harmonics)")
    ax[0].set_xlabel("MHz"); ax[0].set_ylabel("dBV"); ax[0].grid(alpha=.3)

    ax[1].plot((f - fc) / 1e3, dB, lw=0.8, label="FFT")
    ref = 20 * np.log10(np.sqrt(np.sum(lines ** 2)))
    ax[1].plot(k * fm / 1e3, ref + 20 * np.log10(np.abs(jv(k, beta)) + 1e-12),
               "rv", ms=6, label=f"Bessel fit, beta = {beta:.2f}")
    ax[1].set_xlim(-span / 1e3, span / 1e3)
    ax[1].set_ylim(dB.max() - 70, dB.max() + 5)
    ax[1].set_title(f"Zoom around f_c = {fc/1e6:.4f} MHz (lines every {fm/1e3:.0f} kHz)")
    ax[1].set_xlabel("f - f_c [kHz]"); ax[1].set_ylabel("dBV")
    ax[1].grid(alpha=.3); ax[1].legend()
    plt.tight_layout()
    if save:
        plt.savefig(save, dpi=130)
        print(f"\nsaved {save}")
    if show:
        plt.show()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("raw", nargs="?", help="LTspice .raw file")
    p.add_argument("--node", default="V(vout)", help='trace name, e.g. "V(vout)"')
    p.add_argument("--t0", type=float, default=60e-6, help="window start [s] (skip oscillator start-up)")
    p.add_argument("--t1", type=float, default=260e-6, help="window end [s]")
    p.add_argument("--dialect", choices=["ltspice", "ngspice", "qspice", "xyce"],
                   help="simulator that wrote the .raw (auto-detected for LTspice)")
    p.add_argument("--fs", type=float, default=2e9, help="resampling rate [Hz]; keep > 2x highest harmonic")
    p.add_argument("--fm", type=float, default=20e3, help="audio (modulating) frequency [Hz]")
    p.add_argument("--span", type=float, default=300e3, help="zoom half-width around carrier [Hz]")
    p.add_argument("--save", help="save the figure to this file")
    p.add_argument("--no-show", action="store_true", help="don't open a plot window")
    p.add_argument("--demo", action="store_true", help="analyse a synthetic FM signal (beta = 2.405)")
    a = p.parse_args()

    if a.demo:
        t, v = demo_signal(fm=a.fm)
        node = "demo (beta = 2.405)"
    elif a.raw:
        t, v = load_raw(a.raw, a.node, a.dialect)
        node = a.node
    else:
        p.error("give a .raw file or --demo")

    r = analyse(t, v, a.t0, a.t1, a.fs, a.fm, a.span)
    report(r, a.fm)
    plot(r, node, a.fm, a.span, save=a.save, show=not a.no_show)


if __name__ == "__main__":
    main()
