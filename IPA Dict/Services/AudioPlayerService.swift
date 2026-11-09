import AVFoundation
import Foundation

@MainActor
final class AudioPlayerService {
    static let shared = AudioPlayerService()

    private static let spokenLetterNames: [String: String] = [
        "A": "ay",
        "B": "bee",
        "C": "see",
        "D": "dee",
        "E": "ee",
        "F": "eff",
        "G": "gee",
        "H": "aitch",
        "I": "eye",
        "J": "jay",
        "K": "kay",
        "L": "ell",
        "M": "em",
        "N": "en",
        "O": "oh",
        "P": "pee",
        "Q": "cue",
        "R": "are",
        "S": "ess",
        "T": "tee",
        "U": "you",
        "V": "vee",
        "W": "double you",
        "X": "ex",
        "Y": "why"
    ]

    private var remotePlayer: AVPlayer?
    private var speechSynthesizer: AVSpeechSynthesizer?
    private var speechTask: Task<Void, Never>?

    #if os(iOS)
    private static let audioSessionQueue = DispatchQueue(
        label: "AudioPlayerService.audioSession",
        qos: .userInitiated
    )
    #endif

    private init() {}

    func playRemoteSound(url: URL) {
        stopPlayback()
        remotePlayer = AVPlayer(url: url)
        remotePlayer?.volume = 1.0
        remotePlayer?.play()
    }

    func speak(word: String, region: String) {
        let trimmedWord = word.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedWord.isEmpty else {
            return
        }

        let speechText: String
        if trimmedWord == "Z" {
            speechText = region == "UK" ? "zed" : "zee"
        } else {
            speechText = Self.spokenLetterNames[trimmedWord] ?? trimmedWord
        }

        stopPlayback()
        speechTask = Task { @MainActor in
            guard !Task.isCancelled else { return }
            await prepareSpeechAudioSession()
            await Task.yield()
            guard !Task.isCancelled else { return }

            let utterance = AVSpeechUtterance(string: speechText)
            utterance.voice = AVSpeechSynthesisVoice(
                language: region == "UK" ? "en-GB" : "en-US"
            )
            utterance.rate = 0.42
            utterance.volume = 1.0
            let synthesizer = speechSynthesizer ?? AVSpeechSynthesizer()
            speechSynthesizer = synthesizer

            if synthesizer.isSpeaking {
                synthesizer.stopSpeaking(at: .immediate)
            }

            synthesizer.speak(utterance)
            speechTask = nil
        }
    }

    private func stopPlayback() {
        speechTask?.cancel()
        speechTask = nil
        remotePlayer?.pause()
        remotePlayer = nil
        speechSynthesizer?.stopSpeaking(at: .immediate)
    }

    private func prepareSpeechAudioSession() async {
        #if os(iOS)
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            // Session configuration and activation can block, even when a session is already active.
            Self.audioSessionQueue.async {
                defer { continuation.resume() }

                do {
                    let session = AVAudioSession.sharedInstance()
                    if session.category != .playback
                        || session.mode != .spokenAudio
                        || session.categoryOptions != [.duckOthers] {
                        try session.setCategory(
                            .playback,
                            mode: .spokenAudio,
                            options: [.duckOthers]
                        )
                    }
                    try session.setActive(true)
                } catch {
                    print("Unable to prepare speech audio session: \(error.localizedDescription)")
                }
            }
        }
        #endif
    }

}
