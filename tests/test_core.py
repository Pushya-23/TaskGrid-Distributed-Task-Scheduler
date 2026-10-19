from core import compute

def test_prime(): assert compute('prime',{'limit':10})['count']==4
def test_fibonacci(): assert compute('fibonacci',{'count':7})['last']=='8'
def test_statistics(): assert compute('statistics',{'values':[1,2,3]})['average']==2
def test_wordcount(): assert compute('wordcount',{'text':'hello hello world'})['frequencies']['hello']==2
def test_bad_type():
    import pytest
    with pytest.raises(ValueError):compute('other',{})
