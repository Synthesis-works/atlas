import unittest
from unittest.mock import MagicMock

from atlas_db.repositories.query_utils import apply_pagination, apply_sorting, get_paginated_results
from sqlalchemy.orm import Query


class MockModelMetaclass(type):
    def __getattr__(cls, item):
        if item in ("name", "created_at"):
            mock_col = MagicMock()
            mock_col.asc.return_value = f"{item}_asc"
            mock_col.desc.return_value = f"{item}_desc"
            return mock_col
        raise AttributeError(f"type object 'MockModel' has no attribute '{item}'")

class MockModel(metaclass=MockModelMetaclass):
    pass


class TestQueryUtils(unittest.TestCase):
    def setUp(self):
        self.mock_query = MagicMock(spec=Query)
        # Setup chaining
        self.mock_query.limit.return_value = self.mock_query
        self.mock_query.offset.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.count.return_value = 10
        self.mock_query.all.return_value = ["item1", "item2"]

    def test_apply_pagination_limit_only(self):
        result = apply_pagination(self.mock_query, limit=5)
        self.mock_query.limit.assert_called_with(5)
        self.mock_query.offset.assert_not_called()
        self.assertEqual(result, self.mock_query)

    def test_apply_pagination_limit_and_offset(self):
        result = apply_pagination(self.mock_query, limit=5, offset=10)
        self.mock_query.limit.assert_called_with(5)
        self.mock_query.offset.assert_called_with(10)
        self.assertEqual(result, self.mock_query)

    def test_apply_sorting_asc(self):
        result = apply_sorting(self.mock_query, model=MockModel, sort_field="name", order="asc")
        # Ensure order_by was called
        self.assertTrue(self.mock_query.order_by.called)
        self.assertEqual(result, self.mock_query)

    def test_apply_sorting_desc(self):
        result = apply_sorting(self.mock_query, model=MockModel, sort_field="created_at", order="desc")
        self.assertTrue(self.mock_query.order_by.called)
        self.assertEqual(result, self.mock_query)

    def test_apply_sorting_invalid_field(self):
        result = apply_sorting(self.mock_query, model=MockModel, sort_field="invalid_field", order="asc")
        self.mock_query.order_by.assert_not_called()
        self.assertEqual(result, self.mock_query)

    def test_apply_sorting_none_field(self):
        result = apply_sorting(self.mock_query, model=MockModel, sort_field=None, order="asc")
        self.mock_query.order_by.assert_not_called()
        self.assertEqual(result, self.mock_query)

    def test_get_paginated_results(self):
        items, total = get_paginated_results(self.mock_query, limit=5, offset=2)
        
        self.mock_query.count.assert_called_once()
        self.mock_query.limit.assert_called_with(5)
        self.mock_query.offset.assert_called_with(2)
        self.mock_query.all.assert_called_once()
        
        self.assertEqual(total, 10)
        self.assertEqual(items, ["item1", "item2"])
