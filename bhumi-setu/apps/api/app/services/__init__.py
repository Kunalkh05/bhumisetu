"""Domain services (§3.2). Each takes the ambient session as its first argument.

A service never opens a session of its own. It is handed one by the
``unit_of_work()`` block its caller opened, which is what keeps a state change
and its event append in the same transaction (R4.8, §5.2).
"""
