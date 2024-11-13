// Helper function which returns a promise which resolves once the
// service worker registration is past the "installing" state.
function waitUntilInstalled(registration) {
    return new Promise(function(resolve, reject) {
        if (registration.installing) {
            // If the current registration represents the "installing" service worker,
            // then wait until the installation step (during which the resources are
            // pre-fetched) completes to display the file list.
            registration.installing.addEventListener('statechange', function(e) {
                if (e.target.state === 'installed') {
                    resolve();
                } else if (e.target.state === 'redundant') {
                    reject();
                }
            });
        } else {
            // Otherwise, if this isn't the "installing" service worker, then
            // installation must have been completed during a previous visit to this
            // page, and the resources are already pre-fetched.
            resolve();
        }
    });
}

if ('serviceWorker' in navigator) {
navigator.serviceWorker.register('./sw.js', {
    scope: './'
})
    .then(waitUntilInstalled)
    .catch(function(error) {
        // Something went wrong during registration. The service-worker.js file
        // might be unavailable or contain a syntax error.
        console.log("service worker error =>", error);
    });
} else {
    alert('This browser does not support Service Worker. Preloading is not available!');
    console.log('This browser does not support Service Worker. Preloading is not available!');
}
