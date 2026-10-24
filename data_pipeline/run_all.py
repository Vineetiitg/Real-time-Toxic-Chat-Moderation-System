#!/usr/bin/env python3
"""
SafeChat Data Pipeline — Full Pipeline Runner

Runs all 5 steps in sequence:
  Step 1: Download raw datasets from HuggingFace
  Step 2: Unify schemas, clean text, deduplicate
  Step 3: EDA & validation statistics
  Step 4: Multi-label stratified train/val/test split
  Step 5: Final validation & export to training directory

Usage:
    # Run the full pipeline end-to-end
    python -m data_pipeline.run_all

    # Or run individual steps:
    python -m data_pipeline.step1_download
    python -m data_pipeline.step2_unify
    python -m data_pipeline.step3_eda
    python -m data_pipeline.step4_split
    python -m data_pipeline.step5_validate
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Pipeline")


def main():
    logger.info("🚀 SafeChat Data Pipeline — Starting Full Run")
    logger.info("=" * 65)

    logger.info("\n📥 STEP 1/5: Download Raw Datasets")
    logger.info("-" * 65)
    from data_pipeline.step1_download import main as step1
    step1()

    logger.info("\n🔧 STEP 2/5: Unify & Clean")
    logger.info("-" * 65)
    from data_pipeline.step2_unify import main as step2
    step2()

    logger.info("\n📊 STEP 3/5: EDA & Validation")
    logger.info("-" * 65)
    from data_pipeline.step3_eda import main as step3
    step3()

    logger.info("\n✂️ STEP 4/5: Stratified Split")
    logger.info("-" * 65)
    from data_pipeline.step4_split import main as step4
    step4()

    logger.info("\n✅ STEP 5/5: Validate & Export")
    logger.info("-" * 65)
    from data_pipeline.step5_validate import main as step5
    step5()

    logger.info("\n" + "=" * 65)
    logger.info("🎉 FULL PIPELINE COMPLETE — Data is ready for training!")
    logger.info("=" * 65)


if __name__ == "__main__":
    main()

