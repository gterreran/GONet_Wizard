import pytest

@pytest.fixture
def example_GONet_data():

    from GONet_utils import GONetFile
    import numpy as np
    
    array = np.array([range(i,(i+int(GONetFile.PIXEL_PER_LINE*8)), 16) for i in range(0,int(GONetFile.PIXEL_PER_COLUMN*8), 16)])
    red = np.array(array)
    # in GONet we are simply mupltiplying the value by 16, so the saturation is the saturation for a uint12 multiplied by 16, not 2**16-1
    red[red>2**16-1] = (2**12-1)*16
    red = red.astype('uint16')
    green = np.array(array*5)
    green[green>2**16-1] = (2**12-1)*16
    green = green.astype('uint16')
    blue = np.array(array*2)
    blue[blue>2**16-1] = (2**12-1)*16
    blue = blue.astype('uint16')


    test_file = 'Dolus_250307_155311_1741362791.jpg'
    go = GONetFile.from_file(test_file)

    (go.red == red).all()
    (go.green == green).all()
    (go.blue == blue).all()
    return