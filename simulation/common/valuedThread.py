from threading import Thread


class ValuedThread(Thread):
    """
    A subclass of Thread that allows for the thread's target function return value to be captured
    with thread.join()
    Warning: Current implementation is that arguments passed to target will NOT get unpacked. Errors
    may arise if  more than one argument is provided to the thread target.
    """
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(self._args, **self._kwargs)

    def join(self, *args):
        """
        Will wait for the thread's completion, and return the target's return value.

        @rtype: object
        """
        Thread.join(self, *args)
        return self._return
