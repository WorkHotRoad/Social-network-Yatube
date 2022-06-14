
def get_sort_302_feeld(field):
    '''функция возвращает словарь с адресами - кодом 302 '''
    new_list = []
    for k, v in field.items():
        if v == 302:
            new_list.append(k)
    return new_list
