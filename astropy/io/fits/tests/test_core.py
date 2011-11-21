import gzip
import io
import os
import warnings
import zipfile

import numpy as np

from ....io import fits
from ....tests.helper import pytest, raises

from . import FitsTestCase
from ..convenience import _getext


class TestCore(FitsTestCase):
    def test_with_statement(self):
        with fits.open(self.data('ascii.fits')) as f:
            pass

    def test_naxisj_check(self):
        hdulist = fits.open(self.data('o4sp040b0_raw.fits'))

        hdulist[1].header.update("NAXIS3", 500)

        assert 'NAXIS3' in hdulist[1].header
        hdulist.verify('fix')
        assert 'NAXIS3' not in hdulist[1].header

    def test_byteswap(self):
        p = fits.PrimaryHDU()
        l = fits.HDUList()

        n = np.zeros(3, dtype='i2')
        n[0] = 1
        n[1] = 60000
        n[2] = 2

        c = fits.Column(name='foo', format='i2', bscale=1, bzero=32768,
                        array=n)
        t = fits.new_table([c])

        l.append(p)
        l.append(t)

        l.writeto(self.temp('test.fits'), clobber=True)

        p = fits.open(self.temp('test.fits'))
        assert p[1].data[1]['foo'] == 60000.0

    def test_add_del_columns(self):
        p = fits.ColDefs([])
        p.add_col(fits.Column(name='FOO', format='3J'))
        p.add_col(fits.Column(name='BAR', format='1I'))
        assert p.names == ['FOO', 'BAR']
        p.del_col('FOO')
        assert p.names == ['BAR']

    def test_add_del_columns2(self):
        hdulist = fits.open(self.data('tb.fits'))
        table = hdulist[1]
        assert table.data.dtype.names == ('c1', 'c2', 'c3', 'c4')
        assert table.columns.names == ['c1', 'c2', 'c3', 'c4']
        table.columns.del_col('c1')
        assert table.data.dtype.names == ('c2', 'c3', 'c4')
        assert table.columns.names == ['c2', 'c3', 'c4']

        table.columns.del_col('c3')
        assert table.data.dtype.names == ('c2', 'c4')
        assert table.columns.names == ['c2', 'c4']

        table.columns.add_col(fits.Column('foo', '3J'))
        assert table.data.dtype.names == ('c2', 'c4', 'foo')
        assert table.columns.names == ['c2', 'c4', 'foo']

        hdulist.writeto(self.temp('test.fits'), clobber=True)
        hdulist = fits.open(self.temp('test.fits'))
        table = hdulist[1]
        assert table.data.dtype.names == ('c1', 'c2', 'c3')
        assert table.columns.names == ['c1', 'c2', 'c3']

    def test_update_header_card(self):
        """A very basic test for the Header.update method--I'd like to add a
        few more cases to this at some point.
        """

        header = fits.Header()
        comment = 'number of bits per data pixel'
        header.update('BITPIX', 16, comment)
        assert 'BITPIX' in header
        assert header['BITPIX'] == 16
        assert header.ascard['BITPIX'].comment == comment

        header.update('BITPIX', 32, savecomment=True)
        # Make sure the value has been updated, but the comment was preserved
        assert header['BITPIX'] == 32
        assert header.ascard['BITPIX'].comment == comment

        # The comment should still be preserved--savecomment only takes effect if
        # a new comment is also specified
        header.update('BITPIX', 16)
        assert header.ascard['BITPIX'].comment == comment
        header.update('BITPIX', 16, 'foobarbaz', savecomment=True)
        assert header.ascard['BITPIX'].comment == comment

    def test_set_card_value(self):
        """Similar to test_update_header_card(), but tests the the
        `header['FOO'] = 'bar'` method of updating card values.
        """

        header = fits.Header()
        comment = 'number of bits per data pixel'
        card = fits.Card.fromstring('BITPIX  = 32 / %s' % comment)
        header.ascard.append(card)

        header['BITPIX'] = 32

        assert 'BITPIX' in header
        assert header['BITPIX'] == 32
        assert header.ascard['BITPIX'].key == 'BITPIX'
        assert header.ascard['BITPIX'].value == 32
        assert header.ascard['BITPIX'].comment == comment

    def test_uint(self):
        hdulist_f = fits.open(self.data('o4sp040b0_raw.fits'))
        hdulist_i = fits.open(self.data('o4sp040b0_raw.fits'), uint=True)

        assert hdulist_f[1].data.dtype == np.float32
        assert hdulist_i[1].data.dtype == np.uint16
        assert np.all(hdulist_f[1].data == hdulist_i[1].data)

    def test_fix_missing_card_append(self):
        hdu = fits.ImageHDU()
        errs = hdu.req_cards('TESTKW', None, None, 'foo', 'silentfix', [])
        assert len(errs) == 1
        assert 'TESTKW' in hdu.header
        assert hdu.header['TESTKW'] == 'foo'
        assert hdu.header.ascard[-1].key == 'TESTKW'

    def test_fix_invalid_keyword_value(self):
        hdu = fits.ImageHDU()
        hdu.header.update('TESTKW', 'foo')
        errs = hdu.req_cards('TESTKW', None,
                             lambda v: v == 'foo', 'foo', 'ignore', [])
        assert len(errs) == 0

        # Now try a test that will fail, and ensure that an error will be
        # raised in 'exception' mode
        errs = hdu.req_cards('TESTKW', None, lambda v: v == 'bar', 'bar',
                             'exception', [])
        assert len(errs) == 1
        assert errs[0] == "'TESTKW' card has invalid value 'foo'."

        # See if fixing will work
        hdu.req_cards('TESTKW', None, lambda v: v == 'bar', 'bar', 'silentfix',
                      [])
        assert hdu.header['TESTKW'] == 'bar'

    @raises(fits.VerifyError)
    def test_unfixable_missing_card(self):
        class TestHDU(fits.hdu.base.NonstandardExtHDU):
            def _verify(self, option='warn'):
                errs = super(TestHDU, self)._verify(option)
                hdu.req_cards('TESTKW', None, None, None, 'fix', errs)
                return errs

        hdu = TestHDU(header=fits.Header())
        hdu.verify('fix')

    @raises(fits.VerifyError)
    def test_exception_on_verification_error(self):
        hdu = fits.ImageHDU()
        del hdu.header['NAXIS']
        hdu.verify('exception')

    def test_ignore_verification_error(self):
        hdu = fits.ImageHDU()
        # The default here would be to issue a warning; ensure that no warnings
        # or exceptions are raised
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            del hdu.header['NAXIS']
            try:
                hdu.verify('ignore')
            except Exception, e:
                self.fail('An exception occurred when the verification error '
                          'should have been ignored: %s' % e)
        # Make sure the error wasn't fixed either, silently or otherwise
        assert 'NAXIS' not in hdu.header

    @raises(ValueError)
    def test_unrecognized_verify_option(self):
        hdu = fits.ImageHDU()
        hdu.verify('foobarbaz')

    def test_getext(self):
        """
        Test the various different ways of specifying an extension header in
        the convenience functions.
        """

        hl, ext = _getext(self.data('test0.fits'), 'readonly', 1)
        assert ext == 1
        pytest.raises(ValueError, _getext, self.data('test0.fits'), 'readonly',
                      1, 2)
        pytest.raises(ValueError, _getext, self.data('test0.fits'), 'readonly',
                      (1, 2))
        pytest.raises(ValueError, _getext, self.data('test0.fits'), 'readonly',
                      'sci', 'sci')
        pytest.raises(TypeError, _getext, self.data('test0.fits'), 'readonly',
                      1, 2, 3)
        hl, ext = _getext(self.data('test0.fits'), 'readonly', ext=1)
        assert ext == 1
        hl, ext = _getext(self.data('test0.fits'), 'readonly', ext=('sci', 2))
        assert ext == ('sci', 2)
        pytest.raises(TypeError, _getext, self.data('test0.fits'), 'readonly',
                      1, ext=('sci', 2), extver=3)
        pytest.raises(TypeError, _getext, self.data('test0.fits'), 'readonly',
                      ext=('sci', 2), extver=3)

        hl, ext = _getext(self.data('test0.fits'), 'readonly', 'sci')
        assert ext == ('sci', 0)
        hl, ext = _getext(self.data('test0.fits'), 'readonly', 'sci', 1)
        assert ext == ('sci', 1)
        hl, ext = _getext(self.data('test0.fits'), 'readonly', ('sci', 1))
        assert ext == ('sci', 1)
        hl, ext = _getext(self.data('test0.fits'), 'readonly', 'sci',
                          extver=1, do_not_scale_image_data=True)
        assert ext == ('sci', 1)
        pytest.raises(TypeError, _getext, self.data('test0.fits'), 'readonly',
                      'sci', ext=1)
        pytest.raises(TypeError, _getext, self.data('test0.fits'), 'readonly',
                      'sci', 1, extver=2)

        hl, ext = _getext(self.data('test0.fits'), 'readonly', extname='sci')
        assert ext == ('sci', 0)
        hl, ext = _getext(self.data('test0.fits'), 'readonly', extname='sci',
                          extver=1)
        assert ext == ('sci', 1)
        pytest.raises(TypeError, _getext, self.data('test0.fits'), 'readonly',
                      extver=1)


class TestConvenienceFunctions(FitsTestCase):
    def test_writeto(self):
        """
        Simple test for writing a trivial header and some data to a file
        with the `writeto()` convenience function.
        """

        data = np.zeros((100,100))
        header = fits.Header()
        fits.writeto(self.temp('array.fits'), data, header=header,
                     clobber=True)
        hdul = fits.open(self.temp('array.fits'))
        assert len(hdul) == 1
        assert (data == hdul[0].data).all()


class TestFileFunctions(FitsTestCase):
    """
    Tests various basic I/O operations, specifically in the
    astropy.io.fits.file._File class.
    """

    def test_open_gzipped(self):
        assert len(fits.open(self._make_gzip_file())) == 5

    def test_detect_gzipped(self):
        """Test detection of a gzip file when the extension is not .gz."""

        assert len(fits.open(self._make_gzip_file('test0.fz'))) == 5

    def test_open_gzipped_writeable(self):
        """Opening gzipped files in a writeable mode should fail."""

        gf = self._make_gzip_file()
        pytest.raises(IOError, fits.open, gf, 'update')
        pytest.raises(IOError, fits.open, gf, 'append')

    def test_open_zipped(self):
        assert len(fits.open(self._make_zip_file())) == 5

    def test_detect_zipped(self):
        """Test detection of a zip file when the extension is not .zip."""

        zf = self._make_zip_file(filename='test0.fz')
        assert len(fits.open(zf)) == 5

    def test_open_zipped_writeable(self):
        """Opening zipped files in a writeable mode should fail."""

        zf = self._make_zip_file()
        pytest.raises(IOError, fits.open, zf, 'update')
        pytest.raises(IOError, fits.open, zf, 'append')

    @raises(IOError)
    def test_open_multipe_member_zipfile(self):
        """
        Opening zip files containing more than one member files should fail
        as there's no obvious way to specify which file is the FITS file to
        read.
        """

        zfile = zipfile.ZipFile(self.temp('test0.zip'), 'w')
        zfile.write(self.data('test0.fits'))
        zfile.writestr('foo', 'bar')
        zfile.close()

        fits.open(zfile.filename)

    def test_read_open_file(self):
        """Read from an existing file object."""

        with open(self.data('test0.fits'), 'rb') as f:
            assert len(fits.open(f)) == 5

    def test_read_closed_file(self):
        """Read from an existing file object that's been closed."""

        f = open(self.data('test0.fits'), 'rb')
        f.close()
        assert len(fits.open(f)) == 5

    def test_read_open_gzip_file(self):
        """Read from an open gzip file object."""

        gf = gzip.GzipFile(self._make_gzip_file())
        try:
            assert len(fits.open(gf)) == 5
        finally:
            gf.close()

    def test_read_file_like_object(self):
        """Test reading a FITS file from a file-like object."""

        filelike = io.BytesIO()
        with open(self.data('test0.fits'), 'rb') as f:
            filelike.write(f.read())
        filelike.seek(0)
        assert len(fits.open(filelike)) == 5

    def test_updated_file_permissions(self):
        """
        Regression test for #79.  Tests that when a FITS file is modified in
        update mode, the file permissions are preserved.
        """

        filename = self.temp('test.fits')
        hdul = [fits.PrimaryHDU(), fits.ImageHDU()]
        hdul = fits.HDUList(hdul)
        hdul.writeto(filename)

        old_mode = os.stat(filename).st_mode

        hdul = fits.open(filename, mode='update')
        hdul.insert(1, fits.ImageHDU())
        hdul.flush()
        hdul.close()

        assert old_mode == os.stat(filename).st_mode

    def _make_gzip_file(self, filename='test0.fits.gz'):
        gzfile = self.temp(filename)
        with open(self.data('test0.fits'), 'rb') as f:
            gz = gzip.open(gzfile, 'wb')
            gz.write(f.read())
            gz.close()

        return gzfile

    def _make_zip_file(self, mode='copyonwrite', filename='test0.fits.zip'):
        zfile = zipfile.ZipFile(self.temp(filename), 'w')
        zfile.write(self.data('test0.fits'))
        zfile.close()

        return zfile.filename


class TestStreamingFunctions(FitsTestCase):
    """Test functionality of the StreamingHDU class."""

    def test_streaming_hdu(self):
        shdu = self._make_streaming_hdu(self.temp('new.fits'))
        assert isinstance(shdu.size, int)
        assert shdu.size == 100

    @raises(ValueError)
    def test_streaming_hdu_file_wrong_mode(self):
        """
        Test that streaming an HDU to a file opened in the wrong mode fails as
        expected.
        """

        with open(self.temp('new.fits'), 'wb') as f:
            header = fits.Header()
            fits.StreamingHDU(f, header)

    def test_streaming_hdu_write_file(self):
        """Test streaming an HDU to an open file object."""

        arr = np.zeros((5, 5), dtype=np.int32)
        with open(self.temp('new.fits'), 'ab+') as f:
            shdu = self._make_streaming_hdu(f)
            shdu.write(arr)
            assert shdu.writecomplete
            assert shdu.size == 100
        hdul = fits.open(self.temp('new.fits'))
        assert len(hdul) == 1
        assert (hdul[0].data == arr).all()

    def test_streaming_hdu_write_file_like(self):
        """Test streaming an HDU to an open file-like object."""

        arr = np.zeros((5, 5), dtype=np.int32)
        # The file-like object underlying a StreamingHDU must be in binary mode
        sf = io.BytesIO()
        shdu = self._make_streaming_hdu(sf)
        shdu.write(arr)
        assert shdu.writecomplete
        assert shdu.size == 100

        sf.seek(0)
        hdul = fits.open(sf)
        assert len(hdul) == 1
        assert (hdul[0].data == arr).all()

    def test_streaming_hdu_append_extension(self):
        arr = np.zeros((5, 5), dtype=np.int32)
        with open(self.temp('new.fits'), 'ab+') as f:
            shdu = self._make_streaming_hdu(f)
            shdu.write(arr)
        # Doing this again should update the file with an extension
        with open(self.temp('new.fits'), 'ab+') as f:
            shdu = self._make_streaming_hdu(f)
            shdu.write(arr)

    def _make_streaming_hdu(self, fileobj):
        hd = fits.Header()
        hd.update('SIMPLE', True, 'conforms to FITS standard')
        hd.update('BITPIX', 32, 'array data type')
        hd.update('NAXIS', 2, 'number of array dimensions')
        hd.update('NAXIS1', 5)
        hd.update('NAXIS2', 5)
        hd.update('EXTEND', True)
        return fits.StreamingHDU(fileobj, hd)
