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
        prepareSpeechAudioSession()
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

        Task { @MainActor in
            await Task.yield()
            guard !Task.isCancelled else { return }
            synthesizer.speak(utterance)
        }
    }

    private func stopPlayback() {
        remotePlayer?.pause()
        remotePlayer = nil
        speechSynthesizer?.stopSpeaking(at: .immediate)
    }

    private func prepareSpeechAudioSession() {
        #if os(iOS)
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(
                .playback,
                mode: .spokenAudio,
                options: [.duckOthers]
            )
            try session.setActive(true)
        } catch {
            print("Unable to prepare speech audio session: \(error.localizedDescription)")
        }
        #endif
    }

}
