
_COUNT_WORDS = ('burger', 'sandwich')


def unit_for(product):
    name = product.menu_item_name.lower()
    if product.category == 'Drinks':
        return 'ly'
    if any(w in name for w in _COUNT_WORDS):
        return 'chiếc'
    return 'phần'
