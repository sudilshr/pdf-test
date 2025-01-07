import cProfile

def profile_func(func, filename="program"):
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)  # Run the actual function
        profiler.disable()
        # Save profiling results to a file
        profiler.dump_stats(f"{filename}.prof")
        return result
    return wrapper
