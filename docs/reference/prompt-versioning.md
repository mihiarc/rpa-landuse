# AI Prompt Versioning Metrics & Evaluation System

## 1. Key Performance Metrics Framework

### 1.1 Response Quality Metrics

#### Accuracy Metrics
- **Query-to-SQL Accuracy**: Percentage of correctly generated SQL queries
- **Numerical Accuracy**: Deviation from expected values in calculations
- **Entity Recognition Rate**: Correct identification of counties, scenarios, land use types
- **Schema Adherence**: Compliance with database schema constraints

#### Relevance Metrics
- **Response Relevance Score**: Cosine similarity between query and response embeddings
- **Information Completeness**: Coverage of required data points in response
- **Context Utilization Rate**: Percentage of relevant context used
- **Off-topic Detection**: Frequency of irrelevant responses

#### Coherence Metrics
- **Response Consistency**: Contradiction detection across multi-turn conversations
- **Logical Flow Score**: Measure of reasoning chain validity
- **Format Compliance**: Adherence to expected output formats

### 1.2 User Satisfaction Metrics

#### Interaction Metrics
- **First Contact Resolution (FCR)**: Queries resolved without clarification
- **Response Acceptance Rate**: User proceeds with suggested analysis
- **Refinement Frequency**: Number of query reformulations needed
- **Session Completion Rate**: Percentage of sessions ending successfully

#### Quality Indicators
- **Response Time**: P50, P90, P99 latencies
- **Token Efficiency**: Tokens used vs. information conveyed
- **Clarity Score**: Readability metrics (Flesch-Kincaid)
- **Helpfulness Rating**: Explicit user feedback when provided

### 1.3 Task Completion Metrics

#### Success Metrics
- **Task Success Rate**: Percentage of completed analytical tasks
- **Multi-step Completion**: Success rate for complex workflows
- **Tool Usage Effectiveness**: Successful tool invocations vs. attempts
- **Error Recovery Rate**: Successful recovery from initial failures

#### Efficiency Metrics
- **Steps to Completion**: Number of interactions per task
- **Computational Efficiency**: Database query execution time
- **Iteration Efficiency**: Convergence rate to correct solution
- **Resource Utilization**: Memory/CPU usage per query type

### 1.4 Error & Failure Metrics

#### Error Categories
- **SQL Syntax Errors**: Malformed query generation frequency
- **Schema Violations**: Invalid table/column references
- **Logic Errors**: Incorrect aggregations or joins
- **Timeout Failures**: Queries exceeding time limits

#### Recovery Metrics
- **Self-correction Rate**: Autonomous error recovery
- **Fallback Success**: Alternative approach effectiveness
- **Error Message Quality**: Actionable error descriptions
- **Degradation Patterns**: Performance decline indicators

## 2. Evaluation Methodology

### 2.1 Benchmark Suite Design

```python
benchmark_categories = {
    "basic_queries": {
        "description": "Simple single-table queries",
        "examples": [
            "What is the total forest area in 2050?",
            "List all available climate scenarios",
            "Show urban growth in California"
        ],
        "expected_complexity": "LOW",
        "success_threshold": 0.95
    },

    "analytical_queries": {
        "description": "Complex multi-table analysis",
        "examples": [
            "Compare agricultural loss between RCP45 and RCP85 scenarios",
            "Which counties show the most forest to urban conversion?",
            "Analyze land use transitions across all SSP scenarios"
        ],
        "expected_complexity": "MEDIUM",
        "success_threshold": 0.85
    },

    "temporal_analysis": {
        "description": "Time-series and trend analysis",
        "examples": [
            "Show forest loss trends from 2020 to 2100",
            "Calculate decade-over-decade urban growth rates",
            "Project agricultural land availability in 2070"
        ],
        "expected_complexity": "HIGH",
        "success_threshold": 0.80
    },

    "geographic_analysis": {
        "description": "Spatial and regional analysis",
        "examples": [
            "Compare land use changes between Texas and Florida",
            "Which regions are most vulnerable to urbanization?",
            "Analyze coastal county development patterns"
        ],
        "expected_complexity": "HIGH",
        "success_threshold": 0.80
    },

    "edge_cases": {
        "description": "Boundary and error conditions",
        "examples": [
            "Show data for non-existent county",
            "Calculate metrics for year 2200",
            "Compare invalid scenario combinations"
        ],
        "expected_complexity": "ERROR_HANDLING",
        "success_threshold": 0.90
    }
}
```

### 2.2 Automated Testing Framework

```python
class PromptEvaluator:
    def __init__(self, prompt_version: str):
        self.prompt_version = prompt_version
        self.test_results = []

    def run_benchmark_suite(self):
        """Execute comprehensive benchmark tests"""
        results = {
            "version": self.prompt_version,
            "timestamp": datetime.now(),
            "categories": {}
        }

        for category, tests in benchmark_categories.items():
            category_results = self.evaluate_category(category, tests)
            results["categories"][category] = category_results

        return results

    def evaluate_category(self, category: str, tests: dict):
        """Evaluate a specific test category"""
        return {
            "total_tests": len(tests["examples"]),
            "passed": 0,  # Count of successful tests
            "accuracy_score": 0.0,  # Average accuracy
            "latency_p50": 0.0,  # Median response time
            "latency_p99": 0.0,  # 99th percentile response time
            "error_rate": 0.0,  # Percentage of errors
            "details": []  # Individual test results
        }
```

### 2.3 Human Evaluation Framework

```yaml
human_evaluation_criteria:
  response_quality:
    - correctness: "Is the information accurate?"
    - completeness: "Does it answer the full question?"
    - clarity: "Is the response easy to understand?"
    - relevance: "Is all content relevant to the query?"

  technical_accuracy:
    - sql_correctness: "Is the generated SQL valid and correct?"
    - data_interpretation: "Are results interpreted correctly?"
    - calculation_accuracy: "Are computations accurate?"

  user_experience:
    - helpfulness: "Does this help achieve the user's goal?"
    - efficiency: "Is this the most efficient approach?"
    - professionalism: "Is the tone appropriate?"

  scoring_scale:
    - 1: "Completely incorrect/unhelpful"
    - 2: "Major issues"
    - 3: "Acceptable with minor issues"
    - 4: "Good quality"
    - 5: "Excellent/Perfect"
```

### 2.4 Statistical Significance Testing

```python
def compare_prompt_versions(version_a_metrics, version_b_metrics):
    """Statistical comparison of two prompt versions"""

    # Two-sample t-test for continuous metrics
    from scipy import stats

    comparisons = {}

    # Response accuracy comparison
    t_stat, p_value = stats.ttest_ind(
        version_a_metrics["accuracy_scores"],
        version_b_metrics["accuracy_scores"]
    )
    comparisons["accuracy"] = {
        "t_statistic": t_stat,
        "p_value": p_value,
        "significant": p_value < 0.05,
        "effect_size": calculate_cohens_d(
            version_a_metrics["accuracy_scores"],
            version_b_metrics["accuracy_scores"]
        )
    }

    # Chi-square test for categorical outcomes
    success_table = [
        [version_a_metrics["successes"], version_a_metrics["failures"]],
        [version_b_metrics["successes"], version_b_metrics["failures"]]
    ]
    chi2, p_value, dof, expected = stats.chi2_contingency(success_table)
    comparisons["success_rate"] = {
        "chi_square": chi2,
        "p_value": p_value,
        "significant": p_value < 0.05
    }

    return comparisons
```

## 3. Data Collection Strategy

### 3.1 Interaction Logging Schema

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class InteractionLog(BaseModel):
    """Comprehensive interaction logging model"""

    # Identifiers
    session_id: str
    interaction_id: str
    timestamp: datetime

    # Prompt Information
    prompt_version: str
    prompt_hash: str
    system_prompt_length: int

    # Query Details
    user_query: str
    query_embedding: Optional[List[float]]
    query_category: Optional[str]  # Classified category
    query_complexity: Optional[str]  # LOW, MEDIUM, HIGH

    # Response Details
    response_text: str
    response_tokens: int
    response_time_ms: float

    # LLM Details
    model_name: str
    temperature: float
    max_tokens: int

    # Execution Details
    tools_invoked: List[str]
    sql_queries_generated: List[str]
    sql_execution_time_ms: Optional[float]
    rows_returned: Optional[int]

    # Quality Metrics
    error_occurred: bool
    error_type: Optional[str]
    error_message: Optional[str]
    self_corrected: bool

    # User Feedback (if available)
    user_satisfaction: Optional[int]  # 1-5 scale
    user_feedback_text: Optional[str]
    query_reformulated: bool

    # Contextual Information
    conversation_turn: int
    previous_context_used: bool
    memory_tokens_used: int
```

### 3.2 Sampling Strategy for A/B Testing

```python
class ABTestSampler:
    def __init__(self, test_config):
        self.test_config = test_config
        self.assignment_cache = {}

    def assign_variant(self, user_id: str) -> str:
        """Deterministic variant assignment"""

        if user_id in self.assignment_cache:
            return self.assignment_cache[user_id]

        # Consistent hashing for user assignment
        import hashlib
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)

        # Traffic allocation
        if hash_val % 100 < self.test_config["control_percentage"]:
            variant = "control"
        else:
            variant = "treatment"

        self.assignment_cache[user_id] = variant
        return variant

    def stratified_sampling(self, query_category: str) -> bool:
        """Stratified sampling by query category"""

        sampling_rates = {
            "basic_queries": 0.10,      # Sample 10% of basic queries
            "analytical_queries": 0.25,  # Sample 25% of analytical
            "temporal_analysis": 0.50,   # Sample 50% of complex
            "geographic_analysis": 0.50,
            "edge_cases": 1.00          # Sample all edge cases
        }

        import random
        return random.random() < sampling_rates.get(query_category, 0.20)
```

### 3.3 Privacy-Preserving Techniques

```python
class PrivacyPreserver:
    def __init__(self):
        self.pii_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
        ]

    def anonymize_query(self, query: str) -> str:
        """Remove or mask PII from queries"""
        import re

        anonymized = query
        for pattern in self.pii_patterns:
            anonymized = re.sub(pattern, '[REDACTED]', anonymized)

        return anonymized

    def differential_privacy_aggregation(self, metrics: List[float], epsilon: float = 1.0):
        """Add noise for differential privacy"""
        import numpy as np

        sensitivity = max(metrics) - min(metrics) if metrics else 1.0
        noise_scale = sensitivity / epsilon

        noisy_mean = np.mean(metrics) + np.random.laplace(0, noise_scale)
        return max(0, noisy_mean)  # Ensure non-negative
```

## 4. Analysis and Reporting

### 4.1 Performance Dashboard Components

```yaml
dashboard_sections:
  overview:
    - current_version_status
    - active_experiments
    - key_metric_trends
    - alert_summary

  response_quality:
    - accuracy_time_series
    - error_rate_by_category
    - response_time_distribution
    - token_efficiency_trends

  user_satisfaction:
    - satisfaction_scores
    - task_completion_rates
    - session_success_metrics
    - feedback_word_cloud

  comparative_analysis:
    - version_comparison_matrix
    - a_b_test_results
    - statistical_significance_indicators
    - improvement_percentages

  detailed_analytics:
    - query_category_breakdown
    - error_analysis_deep_dive
    - performance_by_model
    - geographic_performance_map
```

### 4.2 Comparison Methodology

```python
class VersionComparator:
    def __init__(self, baseline_version: str, candidate_version: str):
        self.baseline = baseline_version
        self.candidate = candidate_version

    def generate_comparison_report(self) -> Dict:
        """Comprehensive version comparison"""

        return {
            "summary": {
                "baseline_version": self.baseline,
                "candidate_version": self.candidate,
                "evaluation_period": "7_days",
                "total_interactions": 0,
                "recommendation": "PROMOTE|ITERATE|REJECT"
            },

            "metric_comparisons": {
                "accuracy": {
                    "baseline": 0.0,
                    "candidate": 0.0,
                    "change_percent": 0.0,
                    "p_value": 0.0,
                    "significant": False
                },
                "response_time_p50": {
                    "baseline": 0.0,
                    "candidate": 0.0,
                    "change_percent": 0.0,
                    "p_value": 0.0,
                    "significant": False
                },
                "task_completion_rate": {
                    "baseline": 0.0,
                    "candidate": 0.0,
                    "change_percent": 0.0,
                    "p_value": 0.0,
                    "significant": False
                }
            },

            "category_breakdown": {},
            "error_analysis": {},
            "user_feedback_summary": {}
        }
```

### 4.3 Trend Detection

```python
class TrendDetector:
    def __init__(self, window_size: int = 24):  # 24 hours default
        self.window_size = window_size

    def detect_degradation(self, metrics_timeline: List[float]) -> Dict:
        """Detect performance degradation trends"""

        from scipy import stats

        # Mann-Kendall trend test
        trend_result = self.mann_kendall_test(metrics_timeline)

        # Change point detection
        change_points = self.detect_change_points(metrics_timeline)

        # Moving average comparison
        recent_avg = np.mean(metrics_timeline[-self.window_size:])
        historical_avg = np.mean(metrics_timeline[:-self.window_size])

        return {
            "trend_direction": trend_result["trend"],
            "trend_significant": trend_result["p_value"] < 0.05,
            "change_points": change_points,
            "performance_delta": recent_avg - historical_avg,
            "alert_level": self.calculate_alert_level(
                trend_result, change_points, recent_avg, historical_avg
            )
        }
```

### 4.4 Anomaly Detection

```python
class AnomalyDetector:
    def __init__(self, sensitivity: float = 3.0):
        self.sensitivity = sensitivity

    def detect_anomalies(self, metrics: pd.DataFrame) -> List[Dict]:
        """Identify anomalous behavior patterns"""

        anomalies = []

        # Statistical outlier detection
        for column in ['response_time', 'error_rate', 'token_usage']:
            z_scores = np.abs(stats.zscore(metrics[column]))
            outliers = metrics[z_scores > self.sensitivity]

            for idx, row in outliers.iterrows():
                anomalies.append({
                    "timestamp": row['timestamp'],
                    "metric": column,
                    "value": row[column],
                    "z_score": z_scores[idx],
                    "severity": self.classify_severity(z_scores[idx])
                })

        # Pattern-based anomaly detection
        pattern_anomalies = self.detect_pattern_anomalies(metrics)
        anomalies.extend(pattern_anomalies)

        return sorted(anomalies, key=lambda x: x['severity'], reverse=True)
```

## 5. Decision Framework

### 5.1 Promotion Criteria

```python
class PromotionDecisionEngine:
    def __init__(self):
        self.criteria = {
            "minimum_evaluation_period": 7,  # days
            "minimum_sample_size": 1000,     # interactions
            "required_metrics": [
                "accuracy", "response_time", "error_rate", "task_completion"
            ]
        }

    def evaluate_promotion_readiness(self, candidate_metrics: Dict) -> Dict:
        """Determine if a candidate version should be promoted"""

        decision = {
            "ready_for_promotion": False,
            "confidence_score": 0.0,
            "blocking_issues": [],
            "recommendations": []
        }

        # Check minimum requirements
        if candidate_metrics["evaluation_days"] < self.criteria["minimum_evaluation_period"]:
            decision["blocking_issues"].append("Insufficient evaluation period")
            return decision

        if candidate_metrics["total_interactions"] < self.criteria["minimum_sample_size"]:
            decision["blocking_issues"].append("Insufficient sample size")
            return decision

        # Evaluate performance improvements
        performance_scores = {}
        for metric in self.criteria["required_metrics"]:
            improvement = candidate_metrics[f"{metric}_improvement"]
            significance = candidate_metrics[f"{metric}_p_value"] < 0.05

            if metric == "error_rate":
                # Lower is better for error rate
                improvement = -improvement

            performance_scores[metric] = {
                "improved": improvement > 0,
                "significant": significance,
                "magnitude": abs(improvement)
            }

        # Calculate overall confidence score
        confidence_score = self.calculate_confidence_score(performance_scores)
        decision["confidence_score"] = confidence_score

        # Make promotion decision
        if confidence_score >= 0.80:
            decision["ready_for_promotion"] = True
            decision["recommendations"].append("Strong candidate for production")
        elif confidence_score >= 0.60:
            decision["recommendations"].append("Consider limited rollout")
        else:
            decision["blocking_issues"].append("Insufficient performance improvement")

        return decision
```

### 5.2 Rollback Criteria

```python
class RollbackMonitor:
    def __init__(self):
        self.thresholds = {
            "error_rate_increase": 0.20,      # 20% increase triggers alert
            "accuracy_decrease": 0.10,        # 10% decrease triggers alert
            "response_time_increase": 0.50,   # 50% increase triggers alert
            "user_complaints": 5,              # Absolute number in 1 hour
        }

    def evaluate_rollback_need(self, current_metrics: Dict, baseline_metrics: Dict) -> Dict:
        """Determine if rollback is necessary"""

        rollback_decision = {
            "rollback_recommended": False,
            "severity": "NONE",
            "triggered_thresholds": [],
            "metrics_delta": {}
        }

        # Compare against baseline
        for metric, threshold in self.thresholds.items():
            if metric == "user_complaints":
                if current_metrics[metric] > threshold:
                    rollback_decision["triggered_thresholds"].append(metric)
            else:
                baseline_value = baseline_metrics.get(metric, 1.0)
                current_value = current_metrics.get(metric, 1.0)
                delta = (current_value - baseline_value) / baseline_value

                rollback_decision["metrics_delta"][metric] = delta

                if abs(delta) > threshold:
                    rollback_decision["triggered_thresholds"].append(metric)

        # Determine severity and recommendation
        if len(rollback_decision["triggered_thresholds"]) >= 2:
            rollback_decision["rollback_recommended"] = True
            rollback_decision["severity"] = "CRITICAL"
        elif len(rollback_decision["triggered_thresholds"]) == 1:
            rollback_decision["severity"] = "WARNING"

        return rollback_decision
```

### 5.3 Confidence Thresholds

```yaml
confidence_thresholds:
  production_promotion:
    minimum_confidence: 0.80
    required_improvements:
      - accuracy: 0.02  # 2% minimum improvement
      - error_rate: -0.10  # 10% reduction in errors
    statistical_significance: 0.95  # 95% confidence level

  experimental_rollout:
    minimum_confidence: 0.60
    traffic_percentage: 10  # Start with 10% traffic
    escalation_schedule:
      - day_1: 10
      - day_3: 25
      - day_7: 50
      - day_14: 100

  immediate_rollback:
    triggers:
      - error_rate_spike: 0.50  # 50% increase
      - accuracy_drop: 0.20  # 20% decrease
      - response_time_spike: 2.0  # 2x increase
      - critical_errors: 10  # In 5 minutes
```

## 6. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
1. Implement core logging infrastructure
2. Deploy interaction logging schema
3. Set up data collection pipeline
4. Create basic metrics calculation

### Phase 2: Benchmarking (Week 3-4)
1. Develop benchmark test suite
2. Implement automated testing framework
3. Establish baseline metrics
4. Create evaluation scripts

### Phase 3: Analysis (Week 5-6)
1. Build performance dashboard
2. Implement statistical testing
3. Create comparison tools
4. Deploy anomaly detection

### Phase 4: Decision System (Week 7-8)
1. Implement promotion engine
2. Set up rollback monitoring
3. Create alerting system
4. Document decision processes

### Phase 5: Optimization (Ongoing)
1. Refine metrics based on learnings
2. Tune thresholds and parameters
3. Expand benchmark suite
4. Improve automation

## 7. Monitoring and Alerting

```yaml
alert_configurations:
  critical:
    - metric: error_rate
      threshold: 0.10  # 10% error rate
      window: 5m
      action: page_oncall

    - metric: response_time_p99
      threshold: 10000  # 10 seconds
      window: 5m
      action: page_oncall

  warning:
    - metric: accuracy_score
      threshold: 0.80  # Below 80% accuracy
      window: 1h
      action: notify_team

    - metric: user_satisfaction
      threshold: 3.5  # Below 3.5/5 rating
      window: 1d
      action: notify_team

  informational:
    - metric: new_version_deployed
      action: log_event

    - metric: benchmark_completed
      action: update_dashboard
```

## Conclusion

This comprehensive metrics and evaluation system provides:
- **Objective measurement** of prompt performance
- **Automated testing** for rapid iteration
- **Statistical rigor** in decision-making
- **Real-time monitoring** for production safety
- **Data-driven optimization** of prompt engineering

The system balances automation with human oversight, ensuring both efficiency and quality in prompt version management.