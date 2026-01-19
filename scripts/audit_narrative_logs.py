import subprocess
import re
import statistics
from datetime import datetime, timedelta

def get_docker_logs(container_name="sunroom_worker", tail_lines=2000):
    """Fetches logs from a docker container."""
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail_lines), container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.stdout
    except FileNotFoundError:
        print("Error: Docker command not found. Are you running this in a shell with Docker access?")
        return ""
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return ""

def analyze_logs(logs):
    """Parses logs and extracts narrative engine metrics."""
    
    # --- METRICS ---
    tuning_scores = []
    tuning_attempts = []
    
    review_passes = 0
    review_failures = 0
    review_scores = []
    
    planner_activations = 0
    planner_steps_generated = []
    
    state_updates = 0
    
    errors = []
    
    # --- REGEX PATTERNS ---
    # ⚡ Tuning Attempt 1 (plot) | Temp: 0.90 | Score 0.74
    tuning_pattern = re.compile(r"⚡ Tuning Attempt (\d+) .* Score ([\d\.]+)")
    
    # ✅ Review Passed (Score 1.0)
    review_pass_pattern = re.compile(r"✅ Review Passed \(Score ([\d\.]+)\)")
    
    # ❌ Review Failed for Node ...
    review_fail_pattern = re.compile(r"❌ Review Failed")
    
    # 🧠 Planner Generated 8 Steps
    planner_pattern = re.compile(r"📋 Planner Generated (\d+) Steps")
    
    # 📚 State Analyst Updated Ledger
    state_pattern = re.compile(r"📚 State Analyst Updated Ledger")
    
    # ERROR/WARNING lines
    error_pattern = re.compile(r"(ERROR|CRITICAL|Exception).*")

    
    lines = logs.split('\n')
    for line in lines:
        # Tuning
        tune_match = tuning_pattern.search(line)
        if tune_match:
            attempt = int(tune_match.group(1))
            score = float(tune_match.group(2))
            tuning_scores.append(score)
            tuning_attempts.append(attempt)
            
        # Reviewer
        rev_pass = review_pass_pattern.search(line)
        if rev_pass:
            review_passes += 1
            review_scores.append(float(rev_pass.group(1)))
            
        if review_fail_pattern.search(line):
            review_failures += 1
            
        # Planner
        plan_match = planner_pattern.search(line)
        if plan_match:
            planner_activations += 1
            planner_steps_generated.append(int(plan_match.group(1)))
            
        # State
        if state_pattern.search(line):
            state_updates += 1
            
        # Errors (Limit to meaningful ones)
        if "ERROR" in line and "KeyError" not in line: # Skip the one we fixed
             if len(errors) < 10: # Cap error reporting
                 errors.append(line.strip())

    return {
        "tuning": {
            "count": len(tuning_scores),
            "avg_score": statistics.mean(tuning_scores) if tuning_scores else 0,
            "avg_attempts": statistics.mean(tuning_attempts) if tuning_attempts else 0
        },
        "review": {
            "total": review_passes + review_failures,
            "pass_rate": (review_passes / (review_passes + review_failures)) * 100 if (review_passes + review_failures) > 0 else 0,
            "avg_score": statistics.mean(review_scores) if review_scores else 0
        },
        "planner": {
            "activations": planner_activations,
            "avg_steps": statistics.mean(planner_steps_generated) if planner_steps_generated else 0
        },
        "state_updates": state_updates,
        "errors": errors
    }

def print_report(metrics):
    print("\n" + "="*50)
    print(f"🕵️  NARRATIVE ENGINE AUDIT REPORT")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    print(f"\n🧠 CEREBRUM (Planning & Logic)")
    print(f"   Planner Activations:   {metrics['planner']['activations']}")
    if metrics['planner']['activations'] > 0:
        print(f"   Avg Steps per Plan:    {metrics['planner']['avg_steps']:.1f}")
    
    print(f"\n⚡ ENERGY MODEL (Creativity)")
    print(f"   Total Thoughts Tuned:  {metrics['tuning']['count']}")
    if metrics['tuning']['count'] > 0:
        print(f"   Avg Quality Score:     {metrics['tuning']['avg_score']:.2f} / 1.0")
        print(f"   Avg Attempts Needed:   {metrics['tuning']['avg_attempts']:.1f}")
    
    print(f"\n🛡️ ONTOLOGICAL CAGE (Reviewer)")
    print(f"   Total Audits:          {metrics['review']['total']}")
    if metrics['review']['total'] > 0:
        print(f"   Pass Rate:             {metrics['review']['pass_rate']:.1f}%")
        print(f"   Avg Compliance Score:  {metrics['review']['avg_score']:.2f} / 1.0")
    
    print(f"\n📚 NARRATIVE LEDGER (Memory)")
    print(f"   State Updates:         {metrics['state_updates']}")
    
    print(f"\n⚠️ SYSTEM HEALTH (Errors)")
    if metrics['errors']:
        print(f"   Found {len(metrics['errors'])} significant errors:")
        for e in metrics['errors']:
            print(f"   - {e[:100]}...") # Truncate for readability
    else:
        print("   ✅ No critical errors found in recent logs.")
    print("="*50 + "\n")

if __name__ == "__main__":
    print("Fetching logs from 'sunroom_worker'...")
    raw_logs = get_docker_logs()
    if raw_logs:
        metrics = analyze_logs(raw_logs)
        print_report(metrics)
