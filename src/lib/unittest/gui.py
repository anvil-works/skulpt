from . import TestCase, TextTestRunner, defaultTestLoader
import document


class TestCaseGui(TestCase):
    def main(self):
        divid = document.currentDiv()
        results = document.getElementById(divid + '_unit_results')
        if results is None:
            results = document.createElement('pre')
            results.setAttribute('id', divid + '_unit_results')
            results.setAttribute('class', 'unittest-results')
            document.getElementById(divid).appendChild(results)
        results.innerHTML = ''

        class Output(object):
            def write(self, text):
                results.innerHTML += (text.replace('&', '&amp;')
                                      .replace('<', '&lt;').replace('>', '&gt;'))

            def flush(self):
                pass

        suite = defaultTestLoader.loadTestsFromTestCase(type(self))
        return TextTestRunner(stream=Output(), verbosity=2).run(suite)
