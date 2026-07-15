import corpus_pass as cp


def test_count_words():
    assert cp.count_words("one two three") == 3
    assert cp.count_words("  spaced   out  ") == 2
    assert cp.count_words("") == 0


def test_count_sentences():
    assert cp.count_sentences("Hi there. How are you? Great!") == 3
    assert cp.count_sentences("no terminator") == 1
    assert cp.count_sentences("") == 0


def test_avg_sentence_len():
    assert cp.avg_sentence_len("Hi there. How are you?") == 2.5
    assert cp.avg_sentence_len("") == 0.0


def test_count_exclaims_and_questions():
    assert cp.count_exclaims("Wow! Really!") == 2
    assert cp.count_questions("Huh? What?") == 2


def test_count_caps_words():
    assert cp.count_caps_words("This is HUGE and BIG news") == 2
    assert cp.count_caps_words("no caps here") == 0


def test_computers_registry_maps_names():
    assert cp.COMPUTERS["words"]("a b c") == 3
    assert cp.COMPUTERS["avg_sentence_len"]("Hi there. How are you?") == 2.5
