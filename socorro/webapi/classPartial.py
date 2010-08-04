#=================================================================================================================
def classWithPartialInit (C, *args, **kwargs):
  """This function creates a new class W as a subclass of C.  W's __init__ is 
  effectively a partial function of C's __init__.  This allows a class to be
  embued with its initialization parameters long before actual instantiation."""
  class W(C):
    def __init__(self):
      super(W,self).__init__(*args, **kwargs)
  W.__name__ = C.__name__
  return W