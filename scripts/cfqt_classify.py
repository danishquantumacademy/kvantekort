#!/usr/bin/env python3
"""Assigns CFQT v3.0 subdomains to a research title by keyword rules (Danish Quantum Academy).

classify(title) -> list of up to three subdomains, main topic first; [] = outside the CFQT content map.
A title must first pass a relevance check (quantum or condensed-matter / light-matter physics terms);
then each rule that matches adds its weight to a subdomain. The main topic is the subdomain with the
highest score; ties go to the rule listed first. Run this file to see the agreement with the hand-made
classification of PhD and postdoc projects and the Klaus Mølmer test.
"""
import re

R = lambda p: re.compile(p, re.I)

# Relevance: without one of these terms the title is outside the content map.
RELEVANT = R(r"quantum|qubit|qudit|entangl|superpos|decoheren|quantum coheren|coherent (state|control|dynamics)|photon|single[- ]emitter|"
             r"\bspins?\b|spin[- ]|spintron|magnon|squeez|superconduct|josephson|transmon|majorana|topolog|anyon|"
             r"rydberg|cold atom|ultracold|bose[- ]einstein|\bbec\b|fermi gas|trapped ion|\bions?\b.*trap|ion trap|optical lattice|"
             r"\batoms?\b|atomic|laser cool|optomechan|cavity|cavities|\bqed\b|polariton|exciton|plasmon|phonon|"
             r"nitrogen[- ]vacancy|\bnv\b|color cent|colour cent|defect cent|quantum dot|nanowire|2d material|graphene|"
             r"van der waals|moir|twisted|hubbard|many[- ]body|strongly correlated|correlated electron|kagome|"
             r"magnetism|magnon|magnetic (order|phase|material|skyrmion|excitation|anisotrop|moment|field sens)|antiferro|ferromagn|ferroelectr|semiconductor|band structure|electronic structure|density functional|\bdft\b|"
             r"hamiltonian|schr[öo]dinger|lindblad|master equation|open system|non[- ]?hermitian|"
             r"post[- ]quantum|lattice[- ]based crypt|\bqkd\b|key distribution|teleport|bell |nonlocal|"
             r"interferomet|metrolog|magnetomet|gravimet|atomic clock|optical clock|frequency comb|"
             r"superradian|maser|lasing|nonlinear optic|squeezed light|single[- ]photon|waveguide qed|"
             r"cryogen|dilution|millikelvin|nanophotonic|photonic crystal|metasurface|integrated photonic|"
             r"tensor network|variational|grover|\bshor\b|qaoa|vqe|error[- ]correct|fault[- ]toleran|surface code|"
             r"kvante|time crystal|dissipat|matter[- ]wave|jaynes|nondemolition|out[- ]of[- ]time|backaction|back[- ]action|mechanical resonator|wave[- ]?packet|nonclassical|adiabatic|transduc|frequency conversion|neutron scatter|x-ray scatter|muon spin|electron paramagnetic|scanning tunnel|\bstm\b|arpes|"
             r"laser|lithium niobate|microcomb|supercontinuum|fib(er|re) amplif|vcsel|nanolaser|optical commun|photonic|"
             r"light[- ]matter|strongly[- ]correlated|first[- ]principles|ab[- ]initio|electronic propert|oxide interface|lao/sto|"
             r"epitax|nanofab|lithograph|etch process|heterostruct")

# Particle physics, gravity and cosmology are outside the content map even when they say "quantum".
PARTICLE = R(r"quantum gravity|gravit(on|ational wave)|neutrino|\bqcd\b|quark|gluon|lepton|hadron|higgs|collider|\blhc\b|atlas|cms experiment|dark matter|dark energy|cosmolog|black hole|inflation|standard model|supersymmetr|string theor|asymptotic safety|scale symmetry|\bcp\b|cpt symmetry|vector boson|beyond the standard")
# Titles about these are outside the map unless they also say "quantum".
NEGATIVE = R(r"electrochem|oxidation|biosens|gas sens|humidity|hyperthermia|nanoparticles? (for|in) (drug|cancer|therap)|clinical|catalys|catalyt|catalyst|solar cell|photovolta|batter|fuel cell|electrolys|soec|vaccine|drug deliver|biofilm|food|wastewater|co2 |hydrogen production|corrosion|concrete|wind turbine|power system|energy system")

# (pattern, subdomain, weight), more specific rules first.
RULES = [
    # 8 valorisation
    (r"market|business|entrepreneur|start[- ]?up|industr(y|ial) landscape|commerciali", "8.1", 2),
    (r"education|teaching|curricul|student|outreach|popular|fortolkning|interpretation", "8.4", 1),
    (r"ethic|responsib|societ|policy", "8.3", 1),
    # 7 communication
    (r"post[- ]quantum|lattice[- ]based crypt|isogen|kyber|dilithium|quantum[- ]safe|quantum[- ]resist", "7.4", 4),
    (r"\bqkd\b|key distribution|quantum crypt|device[- ]independent", "7.3", 4),
    (r"random number|randomness", "7.2", 3),
    (r"cryptograph|key agreement|authenticat|secure (communication|protocol)", "7.4", 2),
    (r"quantum (internet|network|repeater|memor)|repeater|entanglement distribution|quantum link|frequency conversion|quantum transduc|transducer|heralded entanglement|remote entanglement|quantum memory|memories", "7.5", 3),
    (r"teleport|quantum communication|quantum channel", "7.1", 2),
    (r"blind quantum|distributed quantum|network(ed)? sens", "7.6", 2),
    # 6 sensing
    (r"atomic clock|optical clock|clock transition|frequency standard", "6.6", 4),
    (r"gravimet|gravity|inertial|accelerometer|gyroscop|rotation sens", "6.4", 4),
    (r"magnetomet|magnetic field sens|electric field sens|electrometr|field sens|microwave sens|nv magnet", "6.2", 4),
    (r"thermomet|temperature sens|pressure sens|particle detect|bolomet|single[- ]photon detect|snspd", "6.3", 3),
    (r"quantum imag|ghost imag|sub[- ]?shot[- ]noise imag|quantum microscop|super[- ]resolution", "6.5", 3),
    (r"biomedic|medical|brain|clinical|geophys|navigation|in vivo|cell imag", "6.7", 1),
    (r"nondemolition|backaction|back[- ]action|metrolog|quantum sens|estimation|heisenberg limit|standard quantum limit|squeez|interferomet|precision measure|phase estimat", "6.1", 2),
    (r"sensing|sensor", "6.1", 1),
    # 5 computing
    (r"quantum chemistry on quantum|quantum advantage for|application of quantum comput|quantum machine learn|\bqml\b|quantum (finance|optimi[sz]ation)", "5.6", 3),
    (r"error[- ]correct|fault[- ]toleran|surface code|logical qubit|decoder|compil|quantum software|programming|circuit (optimi|synth)", "5.3", 4),
    (r"quantum simulat|analog simulat|simulate.*with (cold|ultracold|rydberg|trapped)|synthetic gauge|fragmentation|lattice gauge", "5.2", 3),
    (r"grover|\bshor\b|qaoa|vqe|variational quantum|quantum algorithm|quantum walk|amplitude amplif|phase estimation algorithm", "5.5", 4),
    (r"adiabatic quantum|state preparation|quantum subroutine|quantum fourier|oracle", "5.4", 2),
    (r"kvantecomputer|quantum comput|quantum gate|gate operation|multi[- ]?qubit|two[- ]qubit|quantum processor|quantum register|nisq", "5.1", 2),
    # 4 hardware
    (r"superconduct(ing)? (qubit|circuit|resonator|cavity|device|amplif)|transmon|fluxonium|josephson|kinetic inductance|circuit qed|cqed|microwave resonator", "4.1", 4),
    (r"spin qubit|nitrogen[- ]vacancy|\bnv\b|colou?r cent|defect cent|electron spin|nuclear spin|rare[- ]earth|spin ensemble|maser|germanium hole|semiconductor qubit|quantum dot (qubit|spin)", "4.2", 3),
    (r"rydberg|trapped ions?|ion trap|\bions?\b.*(qubit|trap|cool|crystal|clock)|neutral atom|atom array|tweezer|optical lattice|ultracold|cold atom|bose[- ]einstein|\bbec\b", "4.3", 3),
    (r"single[- ]photon (source|emitter)|photonic (qubit|quantum|chip|circuit|integrated)|quantum light|entangled photon|photon pair|parametric down|squeezed light|waveguide qed|photon (sort|subtract|addition)|boson sampling|linear optic|continuous[- ]variable|cluster state|time[- ]bin|temporal mode", "4.4", 3),
    (r"majorana|topological qubit|anyon|cat qubit|bosonic code|gkp|molecular qubit|qudit", "4.5", 3),
    (r"optimal control|quantum control|pulse (shap|design)|qubit readout|spin readout|qubit control|gate fidelit|adiabatic passage|state transfer", "4.6", 3),
    (r"hybrid quantum|quantum[- ]classical|cryo[- ]?cmos|control electronics", "4.7", 3),
    (r"packaging|scal(able|ing) (architecture|fabricat)|wafer|foundry|chip[- ]scale", "4.8", 2),
    # 3 enabling
    (r"cryogen|dilution refriger|millikelvin|vacuum|shield|noise (suppress|reduc)|laser stabili|vibration isol", "3.1", 3),
    (r"nanofab|fabricat|lithograph|epitax|growth|nanowire|thin film|heterostruct|deposition|etch|wafer|2d material|van der waals|graphene|hbn|transition metal dichalcogenide|tmd", "3.2", 2),
    (r"laser|lithium niobate|microcomb|supercontinuum|vcsel|optical commun|grating|optical amplif|fib(er|re)|optical (cavit|resonator|component)|nanophotonic|photonic crystal|metasurface|integrated photonic|lithium niobate|frequency comb|nonlinear optic|silicon photonic|mechanical resonator|optomechan|laser cool", "3.3", 2),
    (r"fpga|control system|feedback control|electronics|microwave (control|engineering)|rf ", "3.4", 2),
    (r"machine learning|neural network|deep learning|software|simulation package|numerical method|tensor network|recurrent", "3.5", 1),
    # 2 physical foundations
    (r"superradian|cavity|cavities|\bqed\b|light[- ]matter|quantum optic|emitter|squeezed|homodyne|heterodyne|jaynes|dicke|polariton|lasing|electrodynamic|nonclassical|jaynes|light pulse|traveling (light|pulse|mode)", "2.2", 2),
    (r"photon|optical|emission|waveguide|radiation|pulse", "2.2", 1),
    (r"\batoms?\b|atomic physics|rydberg|\bions?\b|atomic ensemble|matter[- ]wave|soliton", "2.1", 2),
    (r"molecul|spectroscop", "2.1", 1),
    (r"solid[- ]state|semiconductor|superconductiv|magnetism|magnon|phonon|exciton|band structure|electronic (structure|propert)|kagome|topolog|insulator|quantum dot|moir|twisted|hubbard|correlated electron|fermi liquid|density function|\bdft\b|first[- ]principles|ab[- ]initio|condensed matter|perovskite|oxide|antiferro|ferroelectr|ferromagn|lao/sto|2d material|van der waals|graphene", "2.3", 2),
    (r"magnet|material|crystal|metal|nanowire|\b2d\b|two[- ]?dimensional|spin", "2.3", 1),
    (r"many[- ]body|open (quantum )?system|dissipat|lindblad|master equation|non[- ]?hermitian|time crystal|thermali[sz]|scar|out[- ]of[- ]time|otoc|stochastic schr|quantum trajector|continuous measure|critical|phase transition|spin chain|lattice model|strongly correlated|heisenberg (model|magnet)|ising|statistical mechanic|hamiltonian|strongly[- ]correlated", "2.4", 2),
    # 1 concepts
    (r"entangle|nonlocal|bell |contextual|quantum resource|resource theor|\bchannels?\b|entropy|information theor|mathemat|operator algebra|hilbert space|measurement incompat|quantum catalysis|uncertainty", "1.2", 2),
    (r"kvantemekanik|quantum mechanic|foundation|interpretation|wave ?function|superposition|retrodict|measurement problem|adiabatic theorem|quantum theory|quantum measure", "1.1", 2),
]
RULES = [(R(p), s, w) for p, s, w in RULES]
ORDER = {s: i for i, (_, s, _) in enumerate(RULES)}

def classify(title, max_subs=3):
    t = " " + re.sub(r"\s+", " ", title) + " "
    if not RELEVANT.search(t): return []
    if PARTICLE.search(t) and not re.search(r"qubit|quantum (comput|simulat|sens|inform|technolog)", t, re.I): return []
    if re.match(r"\s*(data (accompanying|for)|supplementary|correction|erratum|retraction)", t, re.I): return []
    if NEGATIVE.search(t) and not re.search(r"quantum|qubit", t, re.I): return []
    score = {}
    for rx, s, w in RULES:
        if rx.search(t): score[s] = score.get(s, 0) + w
    if not score:
        return ["1.1"] if re.search(r"quantum|kvante", t, re.I) else []
    ranked = sorted(score, key=lambda s: (-score[s], ORDER[s]))
    return ranked[:max_subs]

def _evaluate():
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    pairs = []
    for ln in (root / "data/projects/cfqt_projects.txt").read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"): continue
        f = ln.split("|"); subs = f[-1]; title = f[-2]
        pairs.append((title, [] if subs.strip() == "-" else subs.split(";")))
    for ln in (root / "data/people/test_molmer.txt").read_text(encoding="utf-8").splitlines():
        if ln.startswith("O|") or ln.startswith("S|"):
            k, y, s, t = ln.split("|", 3)
            if s != "x": pairs.append((t, s.split(";")))
    n = len(pairs); inout = main_sub = main_dom = main_area = 0; miss = []
    area = lambda s: "I" if s.split(".")[0] in ("1", "2") or s in ("5.1", "5.4", "5.5") else ("III" if s.split(".")[0] == "8" or s in ("5.6", "6.7", "7.4", "7.6") else "II")
    for title, gold in pairs:
        got = classify(title)
        if bool(got) == bool(gold): inout += 1
        if gold and got:
            main_sub += got[0] == gold[0]; main_dom += got[0].split(".")[0] == gold[0].split(".")[0]; main_area += area(got[0]) == area(gold[0])
        if got[:1] != gold[:1]: miss.append((title[:90], gold, got))
    both = sum(1 for t, g in pairs if g and classify(t))
    print(f"{n} titles; in/out of map agree {inout/n:.0%}; of {both} mapped by both: main subdomain {main_sub/both:.0%}, main domain {main_dom/both:.0%}, main area {main_area/both:.0%}")
    return miss

if __name__ == "__main__":
    import sys
    m = _evaluate()
    if "-v" in sys.argv:
        for x in m: print(x)
