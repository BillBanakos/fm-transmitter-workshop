# ngspice

ngspice netlists of the same circuits, for checking LTspice results with a second simulator.
ngspice has no numerical-noise start-up like LTspice, so the oscillator needs a small kick
(e.g. a 1 mA, few-ns current pulse into the tank) to start.

    ngspice -b -r fm_vco.raw fm_vco.cir
    python ../../analysis/fm_fft.py fm_vco.raw --node "v(vout)" --dialect ngspice
