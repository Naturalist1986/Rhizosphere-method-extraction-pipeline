from unittest.mock import MagicMock
from lib.zotero_client import upsert_paper


def test_upsert_paper_skips_if_doi_already_present():
    fake = MagicMock()
    fake.items.return_value = [{"key": "EXISTING", "data": {"DOI": "10.1/x"}}]
    res = upsert_paper(fake, collection_key="COLLKEY",
                       doi="10.1/x", pmid="1", title="t", abstract="a")
    assert res["action"] == "exists"
    assert res["zotero_item_key"] == "EXISTING"
    fake.create_items.assert_not_called()


def test_upsert_paper_creates_when_new():
    fake = MagicMock()
    fake.items.return_value = []
    fake.create_items.return_value = {"successful": {"0": {"key": "NEWKEY"}}}
    res = upsert_paper(fake, collection_key="COLLKEY",
                       doi="10.2/y", pmid=None, title="t", abstract="a")
    assert res["action"] == "created"
    assert res["zotero_item_key"] == "NEWKEY"
