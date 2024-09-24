"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.initBigQuerySync = exports.setupBigQuerySync = exports.fsexportbigquery = exports.syncBigQuery = void 0;
const config_1 = require("./config");
const functions = require("firebase-functions");
const admin = require("firebase-admin");
const extensions_1 = require("firebase-admin/extensions");
const functions_1 = require("firebase-admin/functions");
const firestore_bigquery_change_tracker_1 = require("@firebaseextensions/firestore-bigquery-change-tracker");
const logs = require("./logs");
const events = require("./events");
const util_1 = require("./util");
const eventTracker = new firestore_bigquery_change_tracker_1.FirestoreBigQueryEventHistoryTracker({
    tableId: config_1.default.tableId,
    datasetId: config_1.default.datasetId,
    datasetLocation: config_1.default.datasetLocation,
    backupTableId: config_1.default.backupCollectionId,
    transformFunction: config_1.default.transformFunction,
    timePartitioning: config_1.default.timePartitioning,
    timePartitioningField: config_1.default.timePartitioningField,
    timePartitioningFieldType: config_1.default.timePartitioningFieldType,
    timePartitioningFirestoreField: config_1.default.timePartitioningFirestoreField,
    clustering: config_1.default.clustering,
    wildcardIds: config_1.default.wildcardIds,
    bqProjectId: config_1.default.bqProjectId,
    useNewSnapshotQuerySyntax: config_1.default.useNewSnapshotQuerySyntax,
    skipInit: true,
    kmsKeyName: config_1.default.kmsKeyName,
});
logs.init();
/** Init app, if not already initialized */
if (admin.apps.length === 0) {
    admin.initializeApp();
}
events.setupEventChannel();
exports.syncBigQuery = functions.tasks
    .taskQueue({
    retryConfig: {
        maxAttempts: 5,
        minBackoffSeconds: 60,
    },
    rateLimits: {
        maxConcurrentDispatches: 1000,
        maxDispatchesPerSecond: config_1.default.maxDispatchesPerSecond,
    },
})
    .onDispatch(async ({ context, changeType, documentId, data, oldData }, ctx) => {
    const update = {
        timestamp: context.timestamp,
        operation: changeType,
        documentName: context.resource.name,
        documentId: documentId,
        pathParams: config_1.default.wildcardIds ? context.params : null,
        eventId: context.eventId,
        data,
        oldData,
    };
    /** Record the chnages in the change tracker */
    await eventTracker.record([{ ...update }]);
    /** Send an event Arc update , if configured */
    await events.recordSuccessEvent({
        subject: documentId,
        data: {
            ...update,
        },
    });
    logs.complete();
});
exports.fsexportbigquery = functions
    .runWith({ failurePolicy: true })
    .firestore.document(config_1.default.collectionPath)
    .onWrite(async (change, context) => {
    logs.start();
    try {
        const changeType = (0, util_1.getChangeType)(change);
        const documentId = (0, util_1.getDocumentId)(change);
        const isCreated = changeType === firestore_bigquery_change_tracker_1.ChangeType.CREATE;
        const isDeleted = changeType === firestore_bigquery_change_tracker_1.ChangeType.DELETE;
        const data = isDeleted ? undefined : change.after.data();
        const oldData = isCreated || config_1.default.excludeOldData ? undefined : change.before.data();
        await events.recordStartEvent({
            documentId,
            changeType,
            before: {
                data: change.before.data(),
            },
            after: {
                data: change.after.data(),
            },
            context: context.resource,
        });
        const queue = (0, functions_1.getFunctions)().taskQueue(`locations/${config_1.default.location}/functions/syncBigQuery`, config_1.default.instanceId);
        /**
         * enqueue data cannot currently handle documentdata
         * Serialize early before queueing in clopud task
         * Cloud tasks currently have a limit of 1mb, this also ensures payloads are kept to a minimum
         */
        const seializedData = eventTracker.serializeData(data);
        const serializedOldData = eventTracker.serializeData(oldData);
        await queue.enqueue({
            context,
            changeType,
            documentId,
            data: seializedData,
            oldData: serializedOldData,
        });
    }
    catch (err) {
        await events.recordErrorEvent(err);
        logs.error(err);
        const eventAgeMs = Date.now() - Date.parse(context.timestamp);
        const eventMaxAgeMs = 10000;
        if (eventAgeMs > eventMaxAgeMs) {
            return;
        }
        throw err;
    }
    logs.complete();
});
exports.setupBigQuerySync = functions.tasks
    .taskQueue()
    .onDispatch(async () => {
    /** Setup runtime environment */
    const runtime = (0, extensions_1.getExtensions)().runtime();
    /** Init the BigQuery sync */
    await eventTracker.initialize();
    await runtime.setProcessingState("PROCESSING_COMPLETE", "Sync setup completed");
});
exports.initBigQuerySync = functions.tasks
    .taskQueue()
    .onDispatch(async () => {
    /** Setup runtime environment */
    const runtime = (0, extensions_1.getExtensions)().runtime();
    /** Init the BigQuery sync */
    await eventTracker.initialize();
    /** Run Backfill */
    if (config_1.default.doBackfill) {
        await (0, functions_1.getFunctions)()
            .taskQueue(`locations/${config_1.default.location}/functions/fsimportexistingdocs`, config_1.default.instanceId)
            .enqueue({ offset: 0, docsCount: 0 });
        return;
    }
    await runtime.setProcessingState("PROCESSING_COMPLETE", "Sync setup completed");
    return;
});
exports.fsimportexistingdocs = functions.tasks
    .taskQueue()
    .onDispatch(async (data, context) => {
    const runtime = (0, extensions_1.getExtensions)().runtime();
    if (!config_1.default.doBackfill || !config_1.default.importCollectionPath) {
        await runtime.setProcessingState("PROCESSING_COMPLETE", "Completed. No existing documents imported into BigQuery.");
        return;
    }
    const offset = data["offset"] ?? 0;
    const docsCount = data["docsCount"] ?? 0;
    const query = config_1.default.useCollectionGroupQuery
        ? admin
            .firestore()
            .collectionGroup(config_1.default.importCollectionPath.split("/")[config_1.default.importCollectionPath.split("/").length - 1])
        : admin.firestore().collection(config_1.default.importCollectionPath);
    const snapshot = await query
        .offset(offset)
        .limit(config_1.default.docsPerBackfill)
        .get();
    const rows = snapshot.docs.map((d) => {
        return {
            timestamp: new Date().toISOString(),
            operation: firestore_bigquery_change_tracker_1.ChangeType.IMPORT,
            documentName: `projects/${config_1.default.bqProjectId}/databases/(default)/documents/${d.ref.path}`,
            documentId: d.id,
            eventId: "",
            pathParams: (0, util_1.resolveWildcardIds)(config_1.default.importCollectionPath, d.ref.path),
            data: eventTracker.serializeData(d.data()),
        };
    });
    try {
        await eventTracker.record(rows);
    }
    catch (err) {
        /** If configured, event tracker wil handle failed rows in a backup collection  */
        functions.logger.log(err);
    }
    if (rows.length == config_1.default.docsPerBackfill) {
        // There are more documents to import - enqueue another task to continue the backfill.
        const queue = (0, functions_1.getFunctions)().taskQueue("fsimportexistingdocs", process.env.EXT_INSTANCE_ID);
        await queue.enqueue({
            offset: offset + config_1.default.docsPerBackfill,
            docsCount: docsCount + rows.length,
        });
    }
    else {
        // We are finished, set the processing state to report back how many docs were imported.
        runtime.setProcessingState("PROCESSING_COMPLETE", `Successfully imported ${docsCount + rows.length} documents into BigQuery`);
    }
    await events.recordCompletionEvent({ context });
});
