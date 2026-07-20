import os
import time
import json

def get_metrics(exp_id):
    tasks_dir = os.path.join("results", "experiments", exp_id, "tasks")
    if not os.path.exists(tasks_dir):
        return None
    
    files = [f for f in os.listdir(tasks_dir) if f.endswith(".json")]
    completed = len(files)
    
    passed = 0
    total_gen_time = 0
    for f in files:
        with open(os.path.join(tasks_dir, f), "r") as fp:
            data = json.load(fp)
            if data.get("evaluation_status") == "pass" or data.get("status") == "PASS" or data.get("tests_passed") is True:
                passed += 1
            latency = data.get("generation_latency_ms", 0)
            if latency is not None:
                total_gen_time += latency
            
    pass_at_1 = (passed / completed * 100) if completed > 0 else 0
    avg_gen_time = (total_gen_time / completed) if completed > 0 else 0
    
    return completed, passed, pass_at_1, avg_gen_time

def main():
    exp_id = "exp-mbpp-e509d7"
    thresholds = [250, 500, 750, 974]
    hit_thresholds = set()
    
    print(f"Monitoring {exp_id}...")
    
    while len(hit_thresholds) < len(thresholds):
        metrics = get_metrics(exp_id)
        if metrics:
            completed, passed, pass_at_1, avg_gen_time = metrics
            
            for t in thresholds:
                if completed >= t and t not in hit_thresholds:
                    hit_thresholds.add(t)
                    
                    report = f"""# MBPP Interim Report ({t} tasks)
Experiment: {exp_id}
Completed: {completed}
Passed: {passed}
Pass@1: {pass_at_1:.2f}%
Avg Latency: {avg_gen_time:.2f} ms
"""
                    out_path = f"results/experiments/{exp_id}/interim_report_{t}.md"
                    with open(out_path, "w") as f:
                        f.write(report)
                    print(f"[{time.strftime('%H:%M:%S')}] Saved {out_path} (Pass@1: {pass_at_1:.2f}%)")
                    
        time.sleep(60) # check every minute

if __name__ == "__main__":
    main()
