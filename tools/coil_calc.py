#!/usr/bin/env python3
"""
coil_calc.py - single-layer air-core coil inductance (Wheeler's formula).

    L [uH] = r^2 N^2 / (9 r + 10 l)        r, l in inches

r is the mean coil radius (former diameter + wire diameter) / 2 and l the
winding length. Wheeler is quoted as ~1 % accurate for l > 0.8 r; for short,
fat coils like the ones used at 100 MHz treat the result as a starting point
and tune by stretching / squeezing the turns.

    python coil_calc.py --turns 6.5 --former 3.5 --wire 0.7 --length 5.5
    python coil_calc.py --target 95 --former 3.5 --wire 0.7     # turns vs length table
"""
import argparse

MM_PER_IN = 25.4


def wheeler_nH(turns, former_mm, wire_mm, length_mm):
    r = (former_mm + wire_mm) / 2 / MM_PER_IN
    l = length_mm / MM_PER_IN
    return 1e3 * r * r * turns * turns / (9 * r + 10 * l)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--former", type=float, required=True, help="former / drill-bit diameter [mm]")
    p.add_argument("--wire", type=float, required=True, help="wire diameter [mm]")
    p.add_argument("--turns", type=float, help="number of turns")
    p.add_argument("--length", type=float, help="winding length [mm] (default: close-wound = turns x wire)")
    p.add_argument("--target", type=float, help="target inductance [nH]: print turns/length options")
    a = p.parse_args()

    if a.turns:
        length = a.length or a.turns * a.wire
        L = wheeler_nH(a.turns, a.former, a.wire, length)
        print(f"{a.turns} turns, {a.former} mm former, {a.wire} mm wire, {length:.2f} mm long -> {L:.1f} nH")
        print("\nstretching the same coil:")
        for s in (1.0, 1.25, 1.5, 1.75, 2.0):
            ln = a.turns * a.wire * s
            print(f"  length {ln:5.2f} mm -> {wheeler_nH(a.turns, a.former, a.wire, ln):6.1f} nH")
    if a.target:
        print(f"\noptions for ~{a.target:.0f} nH ({a.former} mm former, {a.wire} mm wire):")
        print("  turns  length[mm]   L[nH]")
        for n2 in range(4, 41):
            n = n2 / 2
            lmin = n * a.wire
            for i in range(400):
                ln = lmin + i * 0.05
                L = wheeler_nH(n, a.former, a.wire, ln)
                if L <= a.target:
                    if i:  # reachable by stretching a close-wound coil
                        print(f"  {n:5.1f}  {ln:9.2f}   {L:6.1f}")
                    break
    if not (a.turns or a.target):
        p.error("give --turns or --target")


if __name__ == "__main__":
    main()
