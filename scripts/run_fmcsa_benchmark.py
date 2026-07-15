from automation.workers.fmcsa_benchmark_worker import (
    run_fmcsa_benchmark,
)


COMPANY_LIMIT = 10
DELAY_SECONDS = 2.0


def main() -> None:
    run_fmcsa_benchmark(
        company_limit=COMPANY_LIMIT,
        delay_seconds=DELAY_SECONDS,
    )


if __name__ == "__main__":
    main()