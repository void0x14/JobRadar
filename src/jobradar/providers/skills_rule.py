"""The no-key fallback: share of the job's required skills found in the profile. It can sort
the Inbox but has no confidence, so it never triggers an alert."""

from __future__ import annotations

import re
from typing import Any

from jobradar.profile import skill_names
from jobradar.providers.base import JobView, MatchAnswers, ProviderName, ProviderUnavailable

_ALIASES = {
    "js": "javascript", "ts": "typescript", "node": "nodejs", "reactjs": "react",
    "nextjs": "next", "postgres": "postgresql", "psql": "postgresql", "mongo": "mongodb",
    "k8s": "kubernetes", "golang": "go", "ml": "machinelearning", "py": "python",
    "restapis": "restapi", "restfulapis": "restapi", "restful": "restapi", "rest": "restapi",
    "restapidesign": "restapi", "html5": "html", "css3": "css", "tailwind": "tailwindcss",
    "expressjs": "express", "gcp": "googlecloud", "amazonwebservices": "aws", "cicd": "cicd",
}  # fmt: skip


# Not technical skills: never shown as "missing", never counted in coverage.
_SOFT = re.compile(
    r"communication|problem[\s-]?solving|team|interpersonal|analytical|leadership|typing|"
    r"attitude|customer|basic|knowledge|learn|presentation|english|time management|"
    r"interpretation|documentation|troubleshooting|support|critical thinking|adaptab|"
    r"programming|coding|computer",
    re.IGNORECASE,
)


def technical(skills: list[str]) -> list[str]:
    return [s for s in skills if not _SOFT.search(s)]


def skill_key(name: str) -> str:
    """'JavaScript (ES6+)' -> 'javascript'; 'Node.js' -> 'nodejs'; 'REST APIs' -> 'restapi'."""
    text = re.sub(r"\([^)]*\)", "", name).casefold()
    key = re.sub(r"[^a-z0-9+#]", "", text)
    return _ALIASES.get(key, key)


_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+#/-]*")

# Technology names a job page may name: the ones the Skills page counts as skills.
COMMON_TECH = {
    "java", "go", "golang", "rust", "c++", "c#", "kotlin", "swift", "scala", "ruby", "php",
    "perl", "dart", "flutter", "typescript", "javascript", "python", "sql", "nosql", "bash",
    "aws", "azure", "gcp", "google cloud", "kubernetes", "k8s", "terraform", "ansible", "helm",
    "kafka", "spark", "hadoop", "airflow", "flink", "rabbitmq", "celery", "temporal",
    "django", "flask", "fastapi", "spring", "spring boot", "laravel", "rails", ".net", "asp.net",
    "angular", "vue", "svelte", "react native", "next.js", "nestjs", "express", "graphql", "grpc",
    "mysql", "postgresql", "sqlite", "mongodb", "dynamodb", "cassandra", "elasticsearch", "redis",
    "snowflake", "bigquery", "docker", "jenkins", "github actions", "gitlab", "linux", "nginx",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy", "opencv", "langchain",
    "llm", "llms", "nlp", "computer vision", "deep learning", "machine learning", "generative ai",
    "microservices", "serverless", "lambda", "s3", "ec2", "kinesis", "websockets", "oauth", "jwt",
    "tableau", "power bi", "excel", "selenium", "playwright", "jest", "pytest", "junit",
}  # fmt: skip


def _ngrams(text: str, longest: int = 3) -> set[str]:
    words = [w.strip(".,;:") for w in _TOKEN.findall(text.replace("**", ""))]
    words = [w for w in words if w]
    grams = set()
    for n in range(1, longest + 1):
        for i in range(len(words) - n + 1):
            grams.add(" ".join(words[i : i + n]))
    return grams


def keys_in(text: str) -> set[str]:
    """Skill keys of every 1-3 word run in the text ('REST APIs' -> 'restapi')."""
    found = set()
    for gram in _ngrams(text):
        key = skill_key(gram)
        found.add(key)
        if "/" in gram:  # "Git/GitHub" mentions Git and GitHub
            found |= {skill_key(p) for p in gram.split("/")}
    return found - {""}


def profile_skill_keys(profile: dict[str, Any]) -> set[str]:
    names = skill_names(profile)  # grouped ({languages: [...]}) or flat
    for project in profile.get("projects", []):
        names += [str(t) for t in project.get("tags", [])]
    keys: set[str] = set()
    for name in names:  # "HTML/CSS" is HTML and CSS too; "JavaScript (ES6+)" is ES6 too
        parts = [name, *re.split(r"/|\s&\s", name), *re.findall(r"\(([^)]*)\)", name)]
        keys |= {skill_key(part) for part in parts}
        keys |= {key.rstrip("+") for key in keys if key[:-1].isalnum()}
    return keys - {""}


def compare_skills(job_skills: list[str], profile: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(the job's skills you have, the job's skills you don't), in the job's wording."""
    have = profile_skill_keys(profile)
    skills = technical(job_skills)
    matched = [s for s in skills if skill_key(s) in have]
    missing = [s for s in skills if skill_key(s) not in have]
    return matched, missing


class SkillsRule:
    name: ProviderName = "skills_rule"

    async def match(self, job: JobView, profile: dict[str, Any]) -> MatchAnswers:
        skills = technical(job.posting.skills_required)
        if not skills:
            raise ProviderUnavailable("the job lists no technical skills")
        matched, _ = compare_skills(skills, profile)
        return MatchAnswers(
            provider=self.name, skills_coverage=round(len(matched) / len(skills), 2)
        )
