import unittest
from unittest.mock import patch, MagicMock
from search_engine import BraveProvider

class TestBraveEngine(unittest.TestCase):

    @patch('requests.get')
    def test_brave_search_extraction(self, mock_get):
        # Simulation de la réponse de l'API Brave
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {"url": "https://brave-result.com/1", "title": "Brave 1"},
                    {"url": "https://brave-result.com/2", "title": "Brave 2"}
                ]
            }
        }
        mock_get.return_value = mock_response

        provider = BraveProvider("fake_key")
        results = provider.search("ai", num_results=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "https://brave-result.com/1")
        # Vérifie que le header de sécurité est bien passé
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs['headers']['X-Subscription-Token'], "fake_key")

if __name__ == '__main__':
    unittest.main()