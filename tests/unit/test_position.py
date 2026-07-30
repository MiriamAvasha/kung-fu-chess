from model.position import Position


class TestPosition:
    def test_equality_and_hash(self):
        a = Position(1, 2)
        b = Position(1, 2)
        c = Position(2, 1)
        assert a == b
        assert a != c
        assert hash(a) == hash(b)
        assert a != (1, 2)

    def test_repr(self):
        assert repr(Position(3, 4)) == 'Position(3, 4)'
