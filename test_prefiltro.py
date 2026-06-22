"""Test offline del prefiltro fellowship (sin API keys)."""
import portales_fellowships as p

SAMPLE_ACCEPT = {
    "titulo": "Remote Fellowship — Open Source",
    "descripcion": "Fully funded scholarship program, stipend available, free to apply.",
}
SAMPLE_REJECT_ISA = {
    "titulo": "Bootcamp with Income Share Agreement",
    "descripcion": "No upfront tuition, pay when you get a job. ISA required.",
}
SAMPLE_REJECT_GIG = {
    "titulo": "AI Data Annotation hourly",
    "descripcion": "Get paid per task for labeling images. Hourly annotation work.",
}


def test_fellowship_keyword_accept():
    assert p.es_fellowship_listing(SAMPLE_ACCEPT["titulo"], SAMPLE_ACCEPT["descripcion"])


def test_isa_penalty_reject():
    assert not p.es_fellowship_listing(SAMPLE_REJECT_ISA["titulo"], SAMPLE_REJECT_ISA["descripcion"])


def test_gig_not_fellowship():
    # gig keywords may pass fellowship filter but evaluador IA lo descarta
    # penalty 'hourly annotation' should filter at portal level
    assert not p.es_fellowship_listing(SAMPLE_REJECT_GIG["titulo"], SAMPLE_REJECT_GIG["descripcion"])


if __name__ == "__main__":
    test_fellowship_keyword_accept()
    test_isa_penalty_reject()
    test_gig_not_fellowship()
    print("# test_prefiltro: OK (3/3)")
