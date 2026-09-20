from installer.post_chroot import uncomment_locale

LOCALE_GEN = "#en_GB.UTF-8 UTF-8\n#en_US.UTF-8 UTF-8\n#en_US ISO-8859-1\n"


def test_uncomment_locale_touches_only_the_matching_line():
    assert uncomment_locale(LOCALE_GEN, "en_US.UTF-8") == (
        "#en_GB.UTF-8 UTF-8\nen_US.UTF-8 UTF-8\n#en_US ISO-8859-1\n"
    )
