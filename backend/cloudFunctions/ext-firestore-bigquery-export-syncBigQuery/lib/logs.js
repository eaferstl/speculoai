"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.timestampMissingValue = exports.start = exports.init = exports.error = exports.dataTypeInvalid = exports.dataInserting = exports.dataInserted = exports.complete = exports.bigQueryViewValidating = exports.bigQueryViewValidated = exports.bigQueryViewUpToDate = exports.bigQueryViewUpdating = exports.bigQueryViewUpdated = exports.bigQueryViewAlreadyExists = exports.bigQueryViewCreating = exports.bigQueryViewCreated = exports.bigQueryUserDefinedFunctionCreated = exports.bigQueryUserDefinedFunctionCreating = exports.bigQueryTableValidating = exports.bigQueryTableValidated = exports.bigQueryTableUpToDate = exports.bigQueryTableUpdating = exports.bigQueryTableUpdated = exports.bigQueryTableCreating = exports.bigQueryTableCreated = exports.bigQueryTableAlreadyExists = exports.bigQueryLatestSnapshotViewQueryCreated = exports.bigQueryErrorRecordingDocumentChange = exports.bigQueryDatasetExists = exports.bigQueryDatasetCreating = exports.bigQueryDatasetCreated = exports.arrayFieldInvalid = void 0;
/*
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
const firebase_functions_1 = require("firebase-functions");
const config_1 = require("./config");
const arrayFieldInvalid = (fieldName) => {
    firebase_functions_1.logger.warn(`Array field '${fieldName}' does not contain an array, skipping`);
};
exports.arrayFieldInvalid = arrayFieldInvalid;
const bigQueryDatasetCreated = (datasetId) => {
    firebase_functions_1.logger.log(`Created BigQuery dataset: ${datasetId}`);
};
exports.bigQueryDatasetCreated = bigQueryDatasetCreated;
const bigQueryDatasetCreating = (datasetId) => {
    firebase_functions_1.logger.log(`Creating BigQuery dataset: ${datasetId}`);
};
exports.bigQueryDatasetCreating = bigQueryDatasetCreating;
const bigQueryDatasetExists = (datasetId) => {
    firebase_functions_1.logger.log(`BigQuery dataset already exists: ${datasetId}`);
};
exports.bigQueryDatasetExists = bigQueryDatasetExists;
const bigQueryErrorRecordingDocumentChange = (e) => {
    firebase_functions_1.logger.error(`Error recording document changes.`, e);
};
exports.bigQueryErrorRecordingDocumentChange = bigQueryErrorRecordingDocumentChange;
const bigQueryLatestSnapshotViewQueryCreated = (query) => {
    firebase_functions_1.logger.log(`BigQuery latest snapshot view query:\n${query}`);
};
exports.bigQueryLatestSnapshotViewQueryCreated = bigQueryLatestSnapshotViewQueryCreated;
const bigQueryTableAlreadyExists = (tableName, datasetName) => {
    firebase_functions_1.logger.log(`BigQuery table with name ${tableName} already ` +
        `exists in dataset ${datasetName}!`);
};
exports.bigQueryTableAlreadyExists = bigQueryTableAlreadyExists;
const bigQueryTableCreated = (tableName) => {
    firebase_functions_1.logger.log(`Created BigQuery table: ${tableName}`);
};
exports.bigQueryTableCreated = bigQueryTableCreated;
const bigQueryTableCreating = (tableName) => {
    firebase_functions_1.logger.log(`Creating BigQuery table: ${tableName}`);
};
exports.bigQueryTableCreating = bigQueryTableCreating;
const bigQueryTableUpdated = (tableName) => {
    firebase_functions_1.logger.log(`Updated existing BigQuery table: ${tableName}`);
};
exports.bigQueryTableUpdated = bigQueryTableUpdated;
const bigQueryTableUpdating = (tableName) => {
    firebase_functions_1.logger.log(`Updating existing BigQuery table: ${tableName}`);
};
exports.bigQueryTableUpdating = bigQueryTableUpdating;
const bigQueryTableUpToDate = (tableName) => {
    firebase_functions_1.logger.log(`BigQuery table: ${tableName} is up to date`);
};
exports.bigQueryTableUpToDate = bigQueryTableUpToDate;
const bigQueryTableValidated = (tableName) => {
    firebase_functions_1.logger.log(`Validated existing BigQuery table: ${tableName}`);
};
exports.bigQueryTableValidated = bigQueryTableValidated;
const bigQueryTableValidating = (tableName) => {
    firebase_functions_1.logger.log(`Validating existing BigQuery table: ${tableName}`);
};
exports.bigQueryTableValidating = bigQueryTableValidating;
const bigQueryUserDefinedFunctionCreating = (functionDefinition) => {
    firebase_functions_1.logger.log(`Creating BigQuery User-defined Function:\n${functionDefinition}`);
};
exports.bigQueryUserDefinedFunctionCreating = bigQueryUserDefinedFunctionCreating;
const bigQueryUserDefinedFunctionCreated = (functionDefinition) => {
    firebase_functions_1.logger.log(`Created BigQuery User-defined Function:\n${functionDefinition}`);
};
exports.bigQueryUserDefinedFunctionCreated = bigQueryUserDefinedFunctionCreated;
const bigQueryViewCreated = (viewName) => {
    firebase_functions_1.logger.log(`Created BigQuery view: ${viewName}`);
};
exports.bigQueryViewCreated = bigQueryViewCreated;
const bigQueryViewCreating = (viewName) => {
    firebase_functions_1.logger.log(`Creating BigQuery view: ${viewName}`);
};
exports.bigQueryViewCreating = bigQueryViewCreating;
const bigQueryViewAlreadyExists = (viewName, datasetName) => {
    firebase_functions_1.logger.log(`View with id ${viewName} already exists in dataset ${datasetName}.`);
};
exports.bigQueryViewAlreadyExists = bigQueryViewAlreadyExists;
const bigQueryViewUpdated = (viewName) => {
    firebase_functions_1.logger.log(`Updated existing BigQuery view: ${viewName}`);
};
exports.bigQueryViewUpdated = bigQueryViewUpdated;
const bigQueryViewUpdating = (viewName) => {
    firebase_functions_1.logger.log(`Updating existing BigQuery view: ${viewName}`);
};
exports.bigQueryViewUpdating = bigQueryViewUpdating;
const bigQueryViewUpToDate = (viewName) => {
    firebase_functions_1.logger.log(`BigQuery view: ${viewName} is up to date`);
};
exports.bigQueryViewUpToDate = bigQueryViewUpToDate;
const bigQueryViewValidated = (viewName) => {
    firebase_functions_1.logger.log(`Validated existing BigQuery view: ${viewName}`);
};
exports.bigQueryViewValidated = bigQueryViewValidated;
const bigQueryViewValidating = (viewName) => {
    firebase_functions_1.logger.log(`Validating existing BigQuery view: ${viewName}`);
};
exports.bigQueryViewValidating = bigQueryViewValidating;
const complete = () => {
    firebase_functions_1.logger.log("Completed execution of extension");
};
exports.complete = complete;
const dataInserted = (rowCount) => {
    firebase_functions_1.logger.log(`Inserted ${rowCount} row(s) of data into BigQuery`);
};
exports.dataInserted = dataInserted;
const dataInserting = (rowCount) => {
    firebase_functions_1.logger.log(`Inserting ${rowCount} row(s) of data into BigQuery`);
};
exports.dataInserting = dataInserting;
const dataTypeInvalid = (fieldName, fieldType, dataType) => {
    firebase_functions_1.logger.warn(`Field '${fieldName}' has invalid data. Expected: ${fieldType}, received: ${dataType}`);
};
exports.dataTypeInvalid = dataTypeInvalid;
const error = (err) => {
    firebase_functions_1.logger.error("Error when mirroring data to BigQuery", err);
};
exports.error = error;
const init = () => {
    firebase_functions_1.logger.log("Initializing extension with configuration", config_1.default);
};
exports.init = init;
const start = () => {
    firebase_functions_1.logger.log("Started execution of extension with configuration", config_1.default);
};
exports.start = start;
const timestampMissingValue = (fieldName) => {
    firebase_functions_1.logger.warn(`Missing value for timestamp field: ${fieldName}, using default timestamp instead.`);
};
exports.timestampMissingValue = timestampMissingValue;
