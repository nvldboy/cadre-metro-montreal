import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP_PAGE = ROOT / "pico" / "setup.html"
PACKAGED_SETUP_PAGE = (
    ROOT
    / "PICO_2_W_PRET_A_COPIER"
    / "CONTENU_A_COPIER_SUR_LE_PICO"
    / "setup.html"
)


class SetupLocalizationTests(unittest.TestCase):
    def test_first_run_assistant_supports_four_languages(self):
        page = SETUP_PAGE.read_text(encoding="utf-8")
        for language in ("fr", "en", "es", "it"):
            self.assertIn('<option value="{}">'.format(language), page)
            self.assertIn("{}: {{".format(language), page)

    def test_language_is_detected_and_remembered_in_the_browser(self):
        page = SETUP_PAGE.read_text(encoding="utf-8")
        self.assertIn("navigator.languages", page)
        self.assertIn('localStorage.getItem("metroSetupLanguage")', page)
        self.assertIn('localStorage.setItem("metroSetupLanguage"', page)
        self.assertIn("document.documentElement.lang = language", page)

    def test_localization_stays_lightweight(self):
        self.assertLess(SETUP_PAGE.stat().st_size, 30_000)

    def test_packaged_setup_page_matches_source(self):
        self.assertEqual(
            PACKAGED_SETUP_PAGE.read_bytes(),
            SETUP_PAGE.read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
